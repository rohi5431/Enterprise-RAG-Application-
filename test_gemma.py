from rag.llm.ollama_client import OllamaClient

client = OllamaClient()

answer = client.generate(
    "What skills are mentioned in Rohit's resume?"
)

print("\nANSWER:")
print(answer)