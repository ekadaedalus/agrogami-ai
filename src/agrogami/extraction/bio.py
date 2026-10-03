"""BIO contracts and constrained token decoding shared by local extraction adapters."""
from math import isfinite
from pydantic import Field, model_validator
from agrogami.schemas import Contract

ENTITIES = ("AMOUNT", "FEE", "BALANCE", "DATE", "TIME", "TXN_ID", "COUNTERPARTY", "TXN_TYPE")
LABELS = ("O",) + tuple(f"{prefix}-{entity}" for entity in ENTITIES for prefix in ("B", "I"))


def valid_transition(previous: str, current: str) -> bool:
    return current in LABELS and (not current.startswith("I-") or previous in {"B-" + current[2:], current})


def validate_bio(labels: tuple[str, ...] | list[str]) -> None:
    previous = "O"
    for label in labels:
        if not valid_transition(previous, label):
            raise ValueError("invalid BIO transition")
        previous = label


def decode_bio(logits: list[list[float]]) -> list[str]:
    """Viterbi over allowed transitions, including the initial O state."""
    states: dict[str, tuple[float, list[str]]] = {"O": (0.0, [])}
    for row in logits:
        if len(row) != len(LABELS) or not all(isfinite(x) for x in row):
            raise ValueError("invalid token logits")
        next_states = {}
        for label, score in zip(LABELS, row):
            choices = [(total + score, path + [label]) for prev, (total, path) in states.items()
                       if valid_transition(prev, label)]
            if choices:
                next_states[label] = max(choices, key=lambda item: item[0])
        states = next_states
    return max(states.values(), key=lambda item: item[0])[1]


class TokenSample(Contract):
    sample_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    text: str
    tokens: tuple[str, ...]
    offsets: tuple[tuple[int, int], ...]
    labels: tuple[str, ...]

    @model_validator(mode="after")
    def alignment(self) -> "TokenSample":
        if len(self.tokens) != len(self.offsets) or len(self.tokens) != len(self.labels):
            raise ValueError("unaligned token annotations")
        validate_bio(self.labels)
        last = 0
        for token, (start, end) in zip(self.tokens, self.offsets):
            if start < last or not start < end <= len(self.text) or self.text[start:end] != token:
                raise ValueError("invalid source offset")
            last = end
        return self


def token_metrics(expected: list[str], predicted: list[str]) -> dict[str, float | int]:
    if not expected or len(expected) != len(predicted):
        raise ValueError("aligned nonempty labels required")
    validate_bio(expected)
    validate_bio(predicted)
    tp = sum(a == b and a != "O" for a, b in zip(expected, predicted))
    fp = sum(b != "O" and a != b for a, b in zip(expected, predicted))
    fn = sum(a != "O" and a != b for a, b in zip(expected, predicted))
    return {"tokens": len(expected), "token_precision": tp / (tp + fp) if tp + fp else 0.0,
            "token_recall": tp / (tp + fn) if tp + fn else 0.0,
            "token_f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0}
