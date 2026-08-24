FROM python:3.11-slim

WORKDIR /app

# Only what the app needs at runtime: the package, the SaaS layer, and the metadata
# pip needs to build the editable-installable package. Tests/docs are not shipped.
COPY pyproject.toml README.md ./
COPY settleflow ./settleflow
COPY saas ./saas

# Install the library + its optional SaaS deps (fastapi/uvicorn/jinja2/multipart).
RUN pip install --no-cache-dir ".[saas]"

EXPOSE 8000
CMD ["uvicorn", "saas.app:app", "--host", "0.0.0.0", "--port", "8000"]
