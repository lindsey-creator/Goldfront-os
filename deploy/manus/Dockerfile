# Build context: Brain/ (parent of goldfront-os + conrad-command-center)
FROM python:3.11-slim
WORKDIR /app
COPY goldfront-os/requirements.txt ./goldfront-os/
RUN pip install --no-cache-dir -r goldfront-os/requirements.txt
COPY goldfront-os/ ./goldfront-os/
COPY conrad-command-center/dist ./conrad-command-center/dist
WORKDIR /app/goldfront-os
ENV GOLDFRONT_OWNER=lindsey
EXPOSE 8000
CMD ["uvicorn", "brain.main:app", "--host", "0.0.0.0", "--port", "8000"]
