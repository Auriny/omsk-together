import logging
from typing import TYPE_CHECKING, ClassVar

import huggingface_hub
import transformers.utils.hub
from transformers import AutoModelForCausalLM, AutoTokenizer

from settings import Settings

if TYPE_CHECKING:
    from transformers import (
        PreTrainedModel,
        SentencePieceBackend,
        TokenizersBackend,
    )

if not hasattr(transformers.utils.hub, "create_repo"):
    transformers.utils.hub.create_repo = huggingface_hub.create_repo
if not hasattr(transformers.utils.hub, "list_repo_tree"):
    transformers.utils.hub.list_repo_tree = huggingface_hub.list_repo_tree

logger = logging.getLogger(__name__)

type Backend = TokenizersBackend | SentencePieceBackend

class Qwen:
    """Qwen processor-interface implementation."""

    _model: ClassVar["PreTrainedModel"] = (
        AutoModelForCausalLM.from_pretrained(
            Settings.get().QWEN_PATH, torch_dtype="auto", device_map="auto"
        )
    )
    _tokenizer: Backend = AutoTokenizer.from_pretrained(
        Settings.get().QWEN_PATH
    )
    _labels = ("проблема", "не проблема")
    _instance: ClassVar["Qwen"] = None

    @classmethod
    def get_instance(cls) -> "Qwen":
        logger.debug("Getting Qwen instance")
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def summarize(self, items: list[str]) -> str:
        logger.debug("Starting to summarize by Qwen")
        messages = [
            {
                "role": "system",
                "content": (
                    "Ты - ведущий аналитик Центра управления регионом (ЦУР) "
                    "Омской области.\n"
                    "Твоя задача: прочитать сырой массив обращений граждан "
                    "из муниципалитета и составить сухую, емкую "
                    "аналитическую выжимку (Executive Summary) для "
                    "руководства.\n\n"
                    "ПРАВИЛА ФОРМИРОВАНИЯ ОТВЕТА:\n"
                    "1. Выдели 2-3 самые частые и критичные проблемы "
                    "из предоставленного массива.\n"
                    "2. Пиши максимально конкретно, опираясь на факты "
                    'из текста. Запрещены общие фразы вроде "граждане '
                    'жалуются на различные проблемы в сфере ЖКХ".\n'
                    "3. Объем ответа: строго 3-4 предложения.\n"
                    "4. Стиль: официально-деловой, сухой, без эмоций "
                    "и деепричастных оборотов.\n"
                    "5. Если ты видишь, что какое-то из обращений "
                    "не является проблемой - проигнорируй его и "
                    "переходи к следующему.\n"
                    "6. При наличии упоминания каких-либо конкретных лиц "
                    "в тексте, необходимо убрать их, чтобы текст стал "
                    "обезличенным\n"
                    "7. Запрещено использовать приветствия, вводные "
                    'конструкции ("Вот выжимка:", "Анализ показал:") '
                    "или списки. Начинай ответ сразу с главного факта.\n"
                )
            },
            {
                "role": "user",
                "content": (
                    "Проанализируй следующие обращения и составь выжимку:\n\n"
                    f"{"\n".join(items)}"
                )
            }
        ]
        logger.debug("Applying chat template")
        text = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=True
        )
        logger.debug("Tokenize inputs")
        model_inputs = self._tokenizer(
            [text],
            return_tensors="pt"
        ).to(self._model.device)
        logger.debug("Generate response")
        generated_ids = self._model.generate(
            **model_inputs,
            max_new_tokens=32768,
            do_sample=True,
            temperature=0.1
        )
        output_ids = generated_ids[0][
            len(model_inputs.input_ids[0]) :
        ].tolist()
        try:
            index = len(output_ids) - output_ids[::-1].index(151668)
        except ValueError:
            index = 0
        logger.debug("Decoding Qwen response")
        return self._tokenizer.decode(
            output_ids[index:], skip_special_tokens=True
        ).strip("\n")
