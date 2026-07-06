"""Multi-brain isolation: each owner's memory is separate; shared is opt-in."""

import tempfile

from brain.memory.knowledge_base import KnowledgeBase
from brain.training.schemas import VoiceExampleIn
from brain.training.service import TrainingService


def test_two_brains_do_not_see_each_other():
    base = tempfile.mkdtemp()
    lindsey = KnowledgeBase(path=base, workspace="lindsey")
    arth = KnowledgeBase(path=base, workspace="ryan-arth")

    lindsey.add_voice("Lindsey private note", recipient="team", context="coaching")

    assert lindsey.count("voice") == 1
    assert arth.count("voice") == 0            # Arth cannot see Lindsey's brain
    assert arth.query("voice", "Lindsey private note") == []


def test_shared_workspace_is_distinct_from_personal():
    base = tempfile.mkdtemp()
    lindsey = KnowledgeBase(path=base, workspace="lindsey")
    shared = KnowledgeBase.shared(path=base)

    shared.add("knowledge", "Goldfront margin floor is 25% vs ARV")
    lindsey.add("knowledge", "Lindsey's private playbook note")

    assert shared.count("knowledge") == 1
    assert lindsey.count("knowledge") == 1     # separate stores, not 2
    # each only sees its own
    assert len(shared.store.all("knowledge")) == 1
    assert len(lindsey.store.all("knowledge")) == 1


def test_training_service_respects_workspace():
    base = tempfile.mkdtemp()
    svc_l = TrainingService(KnowledgeBase(path=base, workspace="lindsey"))
    svc_b = TrainingService(KnowledgeBase(path=base, workspace="ryan-baker"))

    svc_l.train_voice(VoiceExampleIn(text="Lindsey voice sample", recipient="client", context="closing"))
    assert svc_l.counts()["voice"] == 1
    assert svc_b.counts()["voice"] == 0        # Baker's brain is empty and separate
