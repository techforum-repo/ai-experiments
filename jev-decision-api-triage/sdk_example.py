"""One message through the TypeSafe Python SDK, as you would call Jev in production.

  python sdk_example.py
  python sdk_example.py "I have a problem with my order."

Uses the same questions and route() as compare.py. Needs TYPESAFE_API_KEY and
typesafe-sdk (pip install -r requirements.txt).
"""
import json
import sys

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

import decide

QUESTIONS = {
    "category": Choice(instructions=decide.CATEGORY["instructions"],
                       criteria=decide.CATEGORY["options"]),
    "urgent": Noul(instructions=decide.URGENT),
    "impact": Score(instructions=decide.IMPACT["instructions"],
                    criteria=[f"{label}: {text}" for label, text in decide.IMPACT["levels"]]),
    "enough": Noul(instructions=decide.ENOUGH),
}


def main():
    message = sys.argv[1] if len(sys.argv) > 1 else \
        "I'm trying to get my receipt, not reset my account password."
    with TypeSafeClient(model=decide.JEV_MODEL) as client:
        response = client.system_one(message, QUESTIONS)

    category = response.choices["category"]
    print(f"message:  {message}")
    print(f"model:    {response.model}")
    print(f"category: {category.choice} (confidence {category.confidence:.2f})")
    print(f"          {json.dumps(category.probabilities)}")
    print(f"urgent:   {response.nouls['urgent'].noul:.2f}")
    print(f"impact:   {response.scores['impact'].score:.2f} of 2")
    print(f"enough:   {response.nouls['enough'].noul:.2f}")

    answers = decide.normalize_jev(response.model_dump(mode="json"))
    action, reason = decide.route(answers)
    print(f"route:    {action} ({reason})")
    print(f"tokens:   {response.usage.input_tokens} in, {response.usage.output_tokens} out")


if __name__ == "__main__":
    sys.exit(main())
