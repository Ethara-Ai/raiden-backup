from harbor.agents.base import BaseAgent
from harbor.agents.context import AgentContext
from harbor.environments.base import BaseEnvironment


class NullAgent(BaseAgent):
    @staticmethod
    def name() -> str:
        return "null"

    def version(self) -> str:
        return "0.1.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        pass

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        await environment.exec(
            command=(
                'printf "#!/bin/sh\\nexit 0\\n" > /app/awscli && '
                "chmod +x /app/awscli"
            ),
            user="agent",
        )
