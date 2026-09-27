# Talk-back relay (C4/C5). Build from the repo root so pipeline/ and schemas/ are in the context:
#   docker build --platform linux/arm64 -f services/talk/Dockerfile -t yoc-talk .
# Only the three directories below are copied, so .env and data/ never enter the image.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    YOC_DATA=/tmp/yoc AWS_REGION=us-east-1

WORKDIR /app
COPY pipeline/requirements.txt pipeline/requirements.txt
COPY services/talk/requirements.txt services/talk/requirements.txt
# botocore[crt] only exists for `aws login` credentials on a laptop; ECS hands the task role credentials over HTTP.
# Its exact awscrt pin conflicts with smithy-http[awscrt] (awscrt~=0.32), so pip backtracks forever. Drop the extra.
RUN sed 's/botocore\[crt\]/botocore/' pipeline/requirements.txt > /tmp/pipeline-req.txt \
 && pip install --no-cache-dir -r /tmp/pipeline-req.txt -r services/talk/requirements.txt

COPY schemas/ schemas/
COPY pipeline/ pipeline/
COPY services/talk/ services/talk/

RUN useradd --system --uid 10001 --no-create-home talk
USER talk

EXPOSE 8765
# The ALB terminates TLS and adds X-Forwarded-For, so the task trusts it (--behind-alb via YOC_BEHIND_ALB in the
# task definition). A local `docker run` leaves it unset.
ENTRYPOINT ["python", "services/talk/server.py", "--host", "0.0.0.0", "--port", "8765"]
