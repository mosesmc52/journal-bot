import json
import os
import random

import openai
from conversation import Conversation
from dotenv import load_dotenv
from flask import Flask, request
from utils import hasPhrase, period_of_day

app = Flask(__name__)

# find on https://docs.sentry.io/error-reporting/quickstart/?platform=python
# load environmental variables
load_dotenv(".env")

# Load OpenAI Library
openai.api_key = os.getenv("OPENAPI_API_KEY")

conversation = Conversation(
    service_account_file=os.getenv("SERVICE_ACCOUNT_FILE"),
    drive_folder_parent_id=os.getenv("GOOGLE_DRIVE_PARENT_FOLDER_ID"),
    glphy_api_key=os.getenv("GIPHY_API_KEY"),
)

# initialize sentry
if os.getenv("SENTRY_DSN", None):
    import sentry_sdk
    from sentry_sdk import capture_exception

    sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"))


@app.route("/", methods=["GET"])
def helloworld():
    return """Hi, I\'m {}. I here to help you keep track of your memories in life.""".format(
        os.getenv("BOT_NAME")
    )


@app.route("/greeting", methods=["POST"])
def greeting():
    memory = json.loads(request.form["Memory"])
    period = period_of_day(os.getenv("TIMEZONE"))
    first_name = os.getenv("MY_FIRST_NAME", "")
    user_input = request.form.get("CurrentInput")

    conversation.add_content("me", user_input)

    if period == "morning":
        messages = ["Morning, *smile* How are you doing luv?"]
    elif period in ["noon", "afternoon"]:
        messages = ["Good to hear from you, *smile* How are you doing luv?"]
    elif period == "evening":
        messages = ["Good evening, How are doing?"]

    # select random index from message
    random_index = random.randint(0, len(messages) - 1)
    conversation.add_content(os.getenv("BOT_NAME"), messages[random_index], is_bot=True)

    actions = []
    if random.choice([True, False]) and os.getenv(
        "GIPHY_GREETING_QUERY"
    ):  # include greeting query if it exist
        gif = conversation.get_random_glphy(query=os.getenv("GIPHY_GREETING_QUERY"))
        if gif:
            actions.append(
                {
                    "show": {
                        "body": "",
                        "images": [
                            {
                                "label": "",
                                "url": gif,
                            }
                        ],
                    }
                }
            )

    actions.append(
        {
            "collect": {
                "name": "response",
                "questions": [
                    {
                        "question": {"say": messages[random_index]},
                        "name": "response",
                    }
                ],
                "on_complete": {"redirect": "task://share-experience"},
            },
        }
    )

    actions.append(
        {
            "remember": {
                "first_name": os.getenv("MY_FIRST_NAME"),
                "category": "experience",
            }
        }
    )

    return {"actions": actions}


@app.route("/share/experience", methods=["POST"])
def share_experience():
    memory = json.loads(request.form["Memory"])

    if memory["twilio"].get("collected_data"):  # handles input after greeting
        answer = memory["twilio"]["collected_data"]["response"]["answers"]["response"][
            "answer"
        ]
        if memory["twilio"]["collected_data"]["response"]["answers"]["response"].get(
            "media", None
        ):
            mimetype = memory["twilio"]["collected_data"]["response"]["answers"][
                "response"
            ]["media"]["type"]
            url = memory["twilio"]["collected_data"]["response"]["answers"]["response"][
                "media"
            ]["url"]
            conversation.add_media(url=url, mimetype=mimetype)

        category = memory.get("category", "experience")
    else:  # handles fallback input
        answer = request.form.get("CurrentInput")
        if memory.get("media", None):
            mimetype = memory["media"]["type"]
            url = memory["media"]["url"]
            conversation.add_media(url=url, mimetype=mimetype)

        latest_message = conversation.latest_message()
        if latest_message:
            category = latest_message.category or "experience"
        else:
            category = "experience"

    if answer.lower() in ["no", "nothing", "none"] or hasPhrase(
        phrases=["nothing else", "i'm good"], text=answer.lower()
    ):
        conversation.add_content("me", answer, category=category)
        if not conversation.has_reflected_today():
            random_choice = random.randint(0, 1)
            if random_choice:
                messages = [
                    "I want to get to know you better. Can I ask you a question?",
                ]
                random_index = random.randint(0, len(messages) - 1)

                conversation.add_content(
                    os.getenv("BOT_NAME"),
                    messages[random_index],
                    category="reflection",
                    is_bot=True,
                )
                return {
                    "actions": [
                        {
                            "collect": {
                                "name": "response",
                                "questions": [
                                    {
                                        "question": {"say": messages[random_index]},
                                        "name": "response",
                                    }
                                ],
                                "on_complete": {
                                    "redirect": "task://reflection-question"
                                },
                            },
                        },
                    ]
                }

        message = "Thanks for sharing. Talk to you later"
        conversation.add_content(
            os.getenv("BOT_NAME"), message, category=category, is_bot=True
        )
        return {"actions": [{"say": message}]}

    conversation.add_content("me", answer, category=category)

    messages = [
        "Is there anything else you would like to tell me?",
        "** blink ** I want to hear more. Tell me  :)",
    ]

    random_index = random.randint(0, len(messages) - 1)
    conversation.add_content(
        os.getenv("BOT_NAME"), messages[random_index], category=category, is_bot=True
    )

    actions = []
    if random.choice([True, False]) and os.getenv("GIPHY_CURIOUS_QUERY"):
        gif = conversation.get_random_glphy(query=os.getenv("GIPHY_CURIOUS_QUERY"))
        if gif:
            actions.append(
                {
                    "show": {
                        "body": "",
                        "images": [
                            {
                                "label": "",
                                "url": gif,
                            }
                        ],
                    }
                }
            )

    actions.append(
        {
            "collect": {
                "name": "response",
                "questions": [
                    {
                        "question": {"say": messages[random_index]},
                        "name": "response",
                    }
                ],
                "on_complete": {"redirect": "task://share-experience"},
            }
        }
    )

    return {"actions": actions}


@app.route("/share/idea", methods=["POST"])
def share_idea():
    user_input = request.form.get("CurrentInput")
    conversation.add_content("me", user_input)

    message = "Please share your idea. I'm exicted to hear!"
    conversation.add_content(os.getenv("BOT_NAME"), message, is_bot=True)

    return {
        "actions": [
            {
                "collect": {
                    "name": "response",
                    "questions": [{"question": {"say": message}, "name": "response"}],
                    "on_complete": {"redirect": "task://share-experience"},
                },
            },
            {"remember": {"category": "idea"}},
        ]
    }


@app.route("/gratitude", methods=["POST"])
def gratitude():
    user_input = request.form.get("CurrentInput")
    conversation.add_content("me", user_input, category="gratitude")

    message = "Thanks for sharing. It's always good to be thankful!"
    conversation.add_content(os.getenv("BOT_NAME"), message, is_bot=True)

    return {"actions": [{"say": message}]}


@app.route("/question", methods=["POST"])
def openai_response():
    user_input = request.form.get("CurrentInput")
    conversation.add_content_to_tranining_data("me", user_input)
    training_data = conversation.get_training_data()

    response = openai.Completion.create(
        engine="davinci",
        prompt=training_data,
        temperature=0.9,  # This setting controls the randomness of the generated text.  0 deterministic, 1 random baby
        max_tokens=512,
        top_p=1,
        frequency_penalty=1,  # Prevents word repetitions
        presence_penalty=1,  # Prevent topics repetitions
        stop=["me:", "\n"],
    )

    random_index = random.randint(0, len(response.choices) - 1)
    message = response.choices[random_index].text.replace(
        "{}:".format(os.getenv("BOT_NAME")), ""
    )
    conversation.add_content_to_tranining_data(os.getenv("BOT_NAME"), message)

    return {"actions": [{"say": message}, {"listen": True}]}


@app.route("/reflection/question", methods=["POST"])
def reflection_question():
    memory = json.loads(request.form["Memory"])
    answer = memory["twilio"]["collected_data"]["response"]["answers"]["response"][
        "answer"
    ]
    if hasPhrase(phrases=["yes", "go ahead"], text=answer.lower()):
        question = conversation.get_reflection_question()

        if question:
            conversation.add_content(
                os.getenv("BOT_NAME"), question, category="reflection", is_bot=True
            )

            return {
                "actions": [
                    {
                        "collect": {
                            "name": "response",
                            "questions": [
                                {"question": {"say": question}, "name": "response"}
                            ],
                            "on_complete": {"redirect": "task://reflection-response"},
                        },
                    },
                ]
            }

    message = "Okay, we will chat later"

    return {"actions": [{"say": message}]}


@app.route("/reflection/response", methods=["POST"])
def reflection_response():
    # save answer

    # save user response
    memory = json.loads(request.form["Memory"])
    answer = memory["twilio"]["collected_data"]["response"]["answers"]["response"][
        "answer"
    ]

    conversation.add_content("me", answer)

    # bot response
    messages = ["Thanks for sharing. I really enjoy learning more about you."]
    random_index = random.randint(0, len(messages) - 1)
    conversation.add_content(os.getenv("BOT_NAME"), messages[random_index], is_bot=True)

    return {"actions": [{"say": messages[random_index]}]}


@app.route("/fallback", methods=["POST"])
def fallback():
    current_input = request.form.get("CurrentInput").lower()
    tokens = current_input.split(" ")
    if (
        tokens[0]
        in ["who", "did", "whose", "which", "where", "when", "why", "how", "what"]
        or "?" in current_input
    ):
        return {"actions": [{"redirect": "task://question"}]}

    return {"actions": [{"redirect": "task://share-experience"}]}


if __name__ == "__main__":
    app.run()
