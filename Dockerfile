# `python-base` sets up all our shared environment variables
FROM python:3.8.8-buster as python-base


LABEL org.opencontainers.image.authors "Leon Bowie <leon@bowie-co.nz>"
LABEL org.opencontainers.image.source "https://github.com/Obsidion-dev/obsidion"
LABEL org.opencontainers.image.description "Minecraft Discord Bot"
LABEL org.opencontainers.image.licenses "AGPL-3.0+"

# python
ENV PYTHONUNBUFFERED=1 \
    # prevents python creating .pyc files
    PYTHONDONTWRITEBYTECODE=1 \
    \
    # pip
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    \
    # poetry
    # https://python-poetry.org/docs/configuration/#using-environment-variables
    POETRY_VERSION=1.1.5 \
    # make poetry install to this location
    POETRY_HOME="/opt/poetry" \
    # make poetry create the virtual environment in the project's root
    # it gets named `.venv`
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    # do not ask any interactive question
    POETRY_NO_INTERACTION=1 \
    \
    # paths
    # this is where our requirements + virtual environment will live
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"


# prepend poetry and venv to path
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"


# `builder-base` stage is used to build deps + create our virtual environment
FROM python-base as builder-base
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    # deps for installing poetry
    curl \
    # deps for building python deps
    build-essential

# install poetry - respects $POETRY_VERSION & $POETRY_HOME
RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

# copy project requirement files here to ensure they will be cached.
WORKDIR $PYSETUP_PATH
COPY poetry.lock pyproject.toml ./

# install runtime deps - uses $POETRY_VIRTUALENVS_IN_PROJECT internally
RUN poetry install --no-dev


FROM python-base as production
COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH
# quicker install as runtime deps are already installed
COPY ./obsidion /app/obsidion/
COPY ./discord_slash /app/discord_slash/
COPY alembic.ini /app/alembic.ini
COPY start.sh /app/start.sh
COPY ./migrations /app/migrations
WORKDIR /app
CMD ["./start.sh"]
