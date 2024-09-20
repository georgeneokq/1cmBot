FROM python:3.12

WORKDIR /app

# Install poetry and dependencies
RUN pip install poetry
COPY ./poetry.lock ./pyproject.toml .
RUN poetry install

# Copy database management files
COPY ./prisma .

# Copy source code
COPY ./bot/src ./bot/src/

WORKDIR /app/bot

ENTRYPOINT ["poetry", "run", "python3", "src/main.py"]
