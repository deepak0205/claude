"""Tests for ingestion.embedding. The voyageai client is mocked directly -
zero live Voyage API calls."""

from unittest.mock import MagicMock, patch

from ingestion import embedding


def _mock_result(vectors):
    result = MagicMock()
    result.embeddings = vectors
    return result


def setup_function(_):
    # Reset the lazily-initialized module-level client between tests.
    embedding._client = None


def test_embed_documents_uses_document_input_type():
    with patch("ingestion.embedding.voyageai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.embed.return_value = _mock_result([[0.1, 0.2], [0.3, 0.4]])

        result = embedding.embed_documents(["abstract one", "abstract two"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    mock_client.embed.assert_called_once()
    args, kwargs = mock_client.embed.call_args
    assert args[0] == ["abstract one", "abstract two"]
    assert kwargs["input_type"] == "document"


def test_embed_query_uses_query_input_type_and_single_text():
    with patch("ingestion.embedding.voyageai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.embed.return_value = _mock_result([[0.5, 0.6]])

        result = embedding.embed_query("what is EGFR")

    assert result == [0.5, 0.6]
    args, kwargs = mock_client.embed.call_args
    assert args[0] == ["what is EGFR"]
    assert kwargs["input_type"] == "query"


def test_embed_documents_batches_in_groups_of_128():
    texts = [f"doc {i}" for i in range(300)]

    with patch("ingestion.embedding.voyageai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value

        def fake_embed(batch, **kwargs):
            return _mock_result([[0.0] for _ in batch])

        mock_client.embed.side_effect = fake_embed

        result = embedding.embed_documents(texts)

    assert len(result) == 300
    assert mock_client.embed.call_count == 3
    call_batches = [call.args[0] for call in mock_client.embed.call_args_list]
    assert [len(b) for b in call_batches] == [128, 128, 44]


def test_embed_documents_empty_input_makes_no_calls():
    with patch("ingestion.embedding.voyageai.Client") as mock_client_cls:
        result = embedding.embed_documents([])

    assert result == []
    mock_client_cls.assert_not_called()


def test_client_is_lazily_initialized_once():
    with patch("ingestion.embedding.voyageai.Client") as mock_client_cls:
        mock_client_cls.return_value.embed.return_value = _mock_result([[0.1]])
        embedding.embed_query("a")
        embedding.embed_query("b")

    mock_client_cls.assert_called_once()
