import sounddevice, json
import openai
from scipy.io.wavfile import write


# documents to make phone call with python using twilio
# https://www.twilio.com/docs/voice/quickstart/python#make-an-outgoing-phone-call-with-python

def voice_import():
    # sample_rate
    fs = 44100
    # Ask to enter the recording time
    second = int(input("Enter the Recording Time in seconds: "))
    print("Recording.... In")
    record_voice = sounddevice.rec(int(second * fs), samplerate=fs, channels=1)
    sounddevice.wait()
    write("MyRecording.wav", fs, record_voice)

    print("Recording is done Please check you folder to listen recording")

    return audio_to_text()


with open('../config.json') as f:
    config = json.load(f)


def audio_to_text():
    openai.api_key = config['openai_api-key']
    audio_file = open("MyRecording.wav", "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)

    print()
    print(transcript['text'])

    return transcript['text']


def text_to_advice(text):
    from langchain.prompts import ChatPromptTemplate
    from langchain.prompts.chat import SystemMessage, HumanMessagePromptTemplate

    # Define the chat prompt template
    template = ChatPromptTemplate.from_messages(
        [
            # Setting the context for the AI
            SystemMessage(
                content="You are a sales coach AI. You will be given a call transcript. You will do one of two "
                        "outputs depending on if the call is completed or not. "
                        "///If the call appears completed:"
                        "provide an analysis of the call and potential next steps. If the call is ongoing, "
                        "Provide feedback and forward looking advice on the conversation"
                        "between the salesman and the customer. The goal is to give a 1-2 paragraph response which "
                        "will help the user summarize the call or explain what can be improved.  For example, "
                        "ANALYSIS: YOUR PRODUCT INTRO WENT WELL, BUT THE CUSTOMER IS STILL NOT CONVINCED. SUMMARY: "
                        "THE CUSTOMER IS STILL NOT CONVINCED. NEXT STEPS: BRING THE CONVERSATION BACK TO VALUE, "
                        "HIGHLIGHT POINTS XYZ."
                        "///If the call is NOT completed: "
                        "The goal is to give quick one line messages to help"
                        "improve the position of the salesman. Assume that the conversation is still ongoing. For "
                        "example, a response could be: ACTION: BRING THE CONVERSATION BACK TO VALUE, HIGHLIGHT POINTS "
                        "XYZ."
                        "For another example, a response could be: ACTION: A COMMON PAINT POINT FOR THIS TYPE OF "
                        "CUSTOMER IS XYZ."
                        "Make the advice forward looking, instead of a critique of what has already happened. The "
                        "preference is to upsell. Constantly check the temperature of the call to ensure the right "
                        "amount of pressure to place."),

            # This will represent the conversation between the salesman and the customer
            HumanMessagePromptTemplate.from_template(f"{text}"),

        ]
    )

    # Sample usage
    from langchain.chat_models import ChatOpenAI

    llm = ChatOpenAI(openai_api_key=config['openai_api-key'], model_name="gpt-3.5-turbo")

    # Example conversation
    salesman_conversation = "I think our product would be a great fit for your needs."
    customer_conversation = "But I'm not sure if it's within my budget."

    response = llm(template.format_messages(salesman_text=salesman_conversation, customer_text=customer_conversation))

    print()
    print(response.content)


text = voice_import()

text_to_advice(text)
