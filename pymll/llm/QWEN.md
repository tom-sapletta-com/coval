## Qwen2.5-Coder:7B

Najlepsze ustawienia dla modelu Qwen2.5-Coder:7B z maksymalną długością kontekstu 8192 tokenów to:

- max_tokens: 8192 (pełne wykorzystanie kontekstu jest stabilne do co najmniej 16K tokenów, 32K jest też wspierane)
- temperature: 0.2 (niska wartość zwiększa deterministyczność, odpowiednia do generowania kodu)
- retry_attempts: 3 (standardowa liczba prób na wypadek błędów)
- top_p: 1.0 (dla generowania deterministycznego - można dodać, aby kontrolować ryzyko generacji)
- num_return_sequences: 1-4 (dla uzyskania różnych wariantów podpowiedzi, można potem rangować wyniki)
- Zalecane jest stosowanie flagi `trust_remote_code=True` przy ładowaniu modelu w transformers, aby poprawnie obsługiwać niestandardowe osadzenia pozycji (rotary embeddings)

Ustawienia te odpowiadają zaleceniom dla generowania ustrukturyzowanego, niskotemperaturowego, deterministycznego kodu przy rozsądnym oknie 8192 tokenów, z obsługą 3 ponowień przy błędach.[1][2]

[1](https://www.cometapi.com/pl/qwen2-5-features-deploy-comparision/)
[2](https://github.com/zed-industries/zed/issues/18289)
[3](https://www.reddit.com/r/LocalLLaMA/comments/1fkef8s/qwenqwen25coder7binstruct_seems_a_bit_broken/)
[4](https://www.reddit.com/r/LocalLLaMA/comments/1gpwrq1/how_to_use_qwen25coderinstruct_without/)
[5](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct/discussions/16)
[6](https://github.com/continuedev/continue/issues/3372)
[7](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)
[8](https://openrouter.ai/qwen/qwen-2.5-vl-7b-instruct)
[9](https://qwenlm.github.io/blog/qwen2.5-coder-family/)