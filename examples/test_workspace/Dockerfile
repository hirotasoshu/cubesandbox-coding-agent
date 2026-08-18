FROM alpine:3.20

WORKDIR /app
COPY calculator.py .

CMD ["sh", "-c", "test -f calculator.py && echo docker-workspace-ok"]
