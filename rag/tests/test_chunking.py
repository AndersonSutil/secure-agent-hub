from hub_rag.chunking import chunk_text


def test_markdown_splits_at_headings():
    text = "# Um\ntexto um\n# Dois\ntexto dois\n"

    chunks = chunk_text(text, ".md", max_chars=18, overlap=0)

    assert [chunk.text for chunk in chunks] == ["# Um\ntexto um\n", "# Dois\ntexto dois\n"]


def test_luau_splits_at_local_function():
    text = "local function primeiro()\nend\nlocal function segundo()\nend\n"

    chunks = chunk_text(text, ".luau", max_chars=32, overlap=0)

    assert len(chunks) == 2
    assert chunks[0].text.startswith("local function primeiro")
    assert chunks[1].text.startswith("local function segundo")


def test_large_text_is_windowed_with_line_for_second_chunk():
    text = "1234\n5678\nABCDEFGHIJKL"

    chunks = chunk_text(text, ".txt", max_chars=10, overlap=0)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 10 for chunk in chunks)
    assert chunks[1].start_line == 2


def test_empty_text_has_no_chunks():
    assert chunk_text(" \n\t", ".txt") == []
