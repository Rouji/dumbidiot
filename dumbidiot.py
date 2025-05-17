from enum import Enum
from os import environ
from typing import Optional
import pydle
import requests
from dataclasses import dataclass


LLAMA_API_URL = "http://" + environ["LLAMA_HOST"] + "/v1/chat/completions"
IRC_NICK = environ.get("IRC_NICK", "dumbidiot")
IRC_SERVER = environ.get("IRC_SERVER", "irc.libera.chat")
IRC_PORT = int(environ.get("IRC_PORT", 6697))
IRC_CHANNEL = environ["IRC_CHANNEL"]
SYSTEM_PROMPT = environ.get("SYSTEM_PROMPT", "You are a helpful assistant. You always respond in one line, as concisely as possible. ")


class Role(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

@dataclass(frozen=True)
class Message:
    role: Role
    content: str

class DumbIdiotBot(pydle.Client):
    async def on_connect(self):
        await self.join(IRC_CHANNEL)
        self.sysmsg = Message(role=Role.SYSTEM, content=SYSTEM_PROMPT)
        self.messages: list[Message] = [
            self.sysmsg
        ]

    def clamp_irc_message(self, message: str) -> str:
        message = message[:400]
        while len(message.encode('utf-8')) > 400:
            message = message[:-10]
        return message

    def llama(self, message: Message) -> Optional[str]:
        self.messages.append(message)
        payload = {
            "messages": [
                {"role": message.role.value, "content": message.content}
                for message in self.messages
            ],
            "stream": False,
            "cache_prompt": True,
            "samplers": "edkypmxt",
            "temperature": 0.8,
            "dynatemp_range": 0,
            "dynatemp_exponent": 1,
            "top_k": 40,
            "top_p": 0.95,
            "min_p": 0.05,
            "typical_p": 1,
            "xtc_probability": 0,
            "xtc_threshold": 0.1,
            "repeat_last_n": 64,
            "repeat_penalty": 1,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "dry_multiplier": 0,
            "dry_base": 1.75,
            "dry_allowed_length": 2,
            "dry_penalty_last_n": -1,
            "max_tokens": 200,
            "timings_per_token": False,
        }
        response = requests.post(LLAMA_API_URL, json=payload)
        if response.status_code != 200:
            print(f"LLAMA API error: {response.status_code} {response.text}")
            return None
        data = response.json()
        try:
            content = data['choices'][0]['message']['content']
            self.messages.append(Message(role=Role.ASSISTANT, content=content))
            return content
        except (KeyError, IndexError):
            print(f"Invalid response format: {data}")
            return None

    async def on_message(self, target, source, message):
        trigger = self.nickname + ':'
        if source != self.nickname and message.startswith(trigger):
            content = message[len(trigger):].strip()
            if not content:
                return

            result = self.llama(Message(role=Role.USER, content=content))
            if not result:
                return

            result = self.clamp_irc_message(result.replace('\n', ' '))
            if not result:
                return

            if len(self.messages) > 10:
                self.messages = [self.sysmsg] + self.messages[-9:]

            await self.message(target, result)

client = DumbIdiotBot(IRC_NICK, realname='bot')
client.run(IRC_SERVER, port=IRC_PORT, tls=True, tls_verify=False)
