import os
import sys
from argparse import ArgumentParser
from transformers import T5ForConditionalGeneration, T5Tokenizer

base_path = os.environ.get("BASE_PATH") or os.path.dirname(os.path.dirname(__file__))
model_path = os.environ.get("MODEL_PATH") or os.path.join(base_path, "./models/madlad400-3b-mt")


class Translator:
    def __init__(self, model_path: str):
        self.model = T5ForConditionalGeneration.from_pretrained(model_path, device_map="auto")
        self.tokenizer = T5Tokenizer.from_pretrained(model_path)

    def translate(self, target: str, text: str) -> str:
        input_ids = self.tokenizer(f"<2{target}> {text.strip()}", return_tensors="pt").input_ids.to(self.model.device)
        outputs = self.model.generate(input_ids=input_ids, max_length=200)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("text", help="text to be translated", nargs="?")
    parser.add_argument("-t", "--target", help='target language, "en" by default', default="en")
    args = parser.parse_args()

    text = args.text or None
    target = args.target or "en"

    null = open(os.devnull, "w")
    stderr = sys.stderr
    sys.stderr = null

    translator = Translator(model_path)
    if text:
        print(translator.translate(target, text))
    else:
        while True:
            lines = []
            try:
                while True:
                    line = input()
                    if line.endswith("\\"):
                        lines.append(line[:-1])
                    else:
                        lines.append(line)
                        break
            except KeyboardInterrupt:
                if len(lines):
                    print("[Canceled]")
                    continue
                else:
                    break

            try:
                for line in lines:
                    print(translator.translate(target, line))
            except KeyboardInterrupt:
                print("[Canceled]")
                continue
