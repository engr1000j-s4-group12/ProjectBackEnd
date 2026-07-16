from server.app.vlm import VlmClient


def test_dashscope_native_base_url_is_mapped_to_openai_compatible_endpoint() -> None:
    client = VlmClient()
    client.base_url = "https://dashscope.aliyuncs.com/api/v1"
    assert (
        client.chat_completions_url
        == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    )


def test_generic_openai_compatible_base_url_is_preserved() -> None:
    client = VlmClient()
    client.base_url = "https://vlm.example/v1"
    assert client.chat_completions_url == "https://vlm.example/v1/chat/completions"
