# Stage 1: Build dependencies
FROM public.ecr.aws/lambda/python:3.13 as builder

WORKDIR /build

COPY pyproject.toml ./

RUN pip install --no-cache-dir uv && \
    uv pip install --no-cache-dir --target /build/deps --python /var/lang/bin/python3 -r pyproject.toml

# Stage 2: Runtime image
FROM public.ecr.aws/lambda/python:3.13

COPY --from=builder /build/deps ${LAMBDA_RUNTIME_DIR}/

COPY *.py ${LAMBDA_TASK_ROOT}/
COPY providers/ ${LAMBDA_TASK_ROOT}/providers/

CMD [ "main.lambda_handler" ]
