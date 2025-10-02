import pytest
import memebot.chains as chains

def test_chains_basic_lookup():
    # Should contain solana + ethereum by default
    assert "solana" in chains.chains
    assert "ethereum" in chains.chains

def test_unknown_chain_raises():
    with pytest.raises(KeyError):
        _ = chains.chains["does_not_exist"]

