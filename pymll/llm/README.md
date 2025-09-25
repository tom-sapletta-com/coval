# Porównanie modeli kodujących

| Model                         | Data wydania      | Główne korzyści                                                                                                                        |
|--------------------------------|-------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| **deepseek-coder (6.7B)**      | 4 listopada 2023  | - Trening na 2 bilionach tokenów (87% kodu, 13% języka naturalnego)  
- Okno kontekstu 16 K tokenów  
- S.O.T.A. w benchmarkach HumanEval, MBPP, APPS  
- Obsługa projektowego uzupełniania i infillingu kodu [1] |
| **CodeLlama (7B)**             | 23 sierpnia 2023  | - Specjalizacja w syntezie, rozumieniu i edycji kodu  
- Infilling (FIM) i zero-shot instruction following  
- Architektura z Rotary Positional Embeddings  
- Obsługa kontekstu do 100 K tokenów  
- Wydajność konkurencyjna z większymi modelami na Pythonie [2] |
| **CodeLlama (13B)**            | 24 sierpnia 2023  | - 13 mld parametrów dla zaawansowanej generacji i wyjaśnień kodu  
- Udoskonalone FIM i szerokie okno kontekstu 16 K tokenów (z extrapolacją do 100 K)  
- Optymalny kompromis między mocą a wymaganiami sprzętowymi  
- Silny wzrost wydajności względem 7B w złożonych zadaniach [3] |
| **Qwen2.5-Coder (7B)**         | 20 lipca 2025     | - Trening na 5.5 bilionach tokenów z kodem i danymi syntetycznymi  
- Usprawnione generowanie, rozumowanie i naprawa kodu  
- Pełne wsparcie kontekstu do 131 072 tokenów  
- Architektura RoPE, SwiGLU, RMSNorm i GQA  
- Podstawa dla agentów kodujących i zaawansowanych workflowów [4] |
| **Granite-Code (8B)**          | 6 maja 2024       | - Dwuetapowy trening: 4 biliony tokenów z 116 języków, następnie 500 mld wysokiej jakości danych  
- Generator kodu, wyjaśnienia i naprawa błędów  
- Udoskonalone zdolności wnioskowania i podążania za instrukcjami  
- Licencja Apache 2.0, gotowy do zastosowań enterprise [5] |
| **Mistral (7B)**               | 27 września 2023  | - 7.3 mld parametrów z GQA i Sliding-Window Attention  
- Okno kontekstu do 8 192 tokenów  
- Przewyższa Llama 2 13B w benchmarkach i zbliża się do CodeLlama 7B w kodzie  
- Wersja v0.3 z obsługą wywołań funkcji  
- Lekka, szybka i bezrestrykcyjna licencja Apache 2.0 [6] |

[1](https://huggingface.co/TheBloke/deepseek-coder-6.7B-base-GGUF)
[2](https://www.emergentmind.com/topics/codellama-7b)
[3](https://www.byteplus.com/en/topic/504702)
[4](https://huggingface.co/Qwen/Qwen2.5-Coder-7B)
[5](https://huggingface.co/ibm-granite/granite-8b-code-base-4k)
[6](https://openlaboratory.ai/models/mistral-7b)
[7](https://www.byteplus.com/en/topic/417596)
[8](https://www.byteplus.com/en/topic/431039)
[9](https://www.byteplus.com/en/topic/504638)
[10](https://www.dhiwise.com/post/deepseek-coder-ai-code-intelligence)
[11](https://ai.meta.com/blog/code-llama-large-language-model-coding/)
[12](https://huggingface.co/codellama/CodeLlama-13b-hf)
[13](https://www.revechat.com/blog/what-is-deepseek/)
[14](https://builds.modular.com/models/CodeLlama-Instruct-hf/7B)
[15](https://www.qt.io/blog/codellama-13b-qml-released-on-hugging-face)
[16](https://www.byteplus.com/en/topic/418262)
[17](https://huggingface.co/meta-llama/CodeLlama-7b-hf)
[18](https://builds.modular.com/models/CodeLlama-Instruct-hf/13B)
[19](https://model.aibase.com/models/details/1915693835444969474)
[20](https://huggingface.co/TheBloke/CodeLlama-7B-Instruct-GGUF)
[21](https://docs.ionos.com/cloud/ai/ai-model-hub/models/meta-code-llama-13b)
[22](https://ollama.com/library/deepseek-coder:6.7b/blobs/a3a0e9449cb6)
[23](https://console.cloud.google.com/vertex-ai/publishers/meta/model-garden/codellama-7b-hf?hl=ja)
[24](https://huggingface.co/unsloth/Qwen2.5-Coder-7B)
[25](https://ollama.com/ashishpatel26/granite-8b-code)
[26](https://mistral.ai/news/announcing-mistral-7b)
[27](https://openrouter.ai/qwen/qwen2.5-coder-7b-instruct)
[28](https://huggingface.co/ibm-granite/granite-3.3-8b-instruct)
[29](https://lunabot.ai/en/models/mistral-7b)
[30](https://openlaboratory.ai/models/qwen-2_5-coder-7b)
[31](https://www.ibm.com/new/announcements/ibm-granite-3-2-open-source-reasoning-and-vision)
[32](https://ollama.com/library/mistral:7b)
[33](https://www.byteplus.com/en/topic/398309)
[34](https://www.ibm.com/granite/docs/models/granite)
[35](https://docs.ionos.com/cloud/ai/ai-model-hub/models/mistral-7b)
[36](https://ollama.com/library/qwen2.5-coder:7b)
[37](https://build.nvidia.com/ibm/granite-3_3-8b-instruct/modelcard)
[38](https://huggingface.co/mistralai/Mistral-7B-v0.1)
[39](https://llm-stats.com/models/compare/mistral-small-3-vs-qwen-2.5-coder-7b-instruct)
[40](https://en.wikipedia.org/wiki/IBM_Granite)