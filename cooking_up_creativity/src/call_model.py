import openai
from .api_secrets import API_KEY
import backoff

openai.api_key = API_KEY

if not API_KEY:
    print("Warning: OpenAI API key is not set. Please set the API_KEY variable in api_secrets.py and run the code again.")
    input()

@backoff.on_exception(backoff.expo, (openai.error.RateLimitError, openai.error.ServiceUnavailableError), max_time=60)  # this catches rate errors and server errors and retries in exponential time steps
def call_model(request, model_name, system_message, temperature=0.0, max_tokens=50, stop=None):

    try:
        completion = openai.ChatCompletion.create(
            model=model_name,
            messages=[{"role": "system", "content": system_message},
                      {"role": "user", "content": request}],
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop
        )

        response = completion["choices"][0]["message"]["content"]

    except (openai.error.RateLimitError, openai.error.APIError) as e:
        print("Exception occurred: ", str(e))
        return None

    return response


