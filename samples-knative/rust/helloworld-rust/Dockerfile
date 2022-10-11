# Use the official Rust image.
# https://hub.docker.com/_/rust
FROM rust:1.62.1 as builder

# Copy local code to the container image.
WORKDIR /usr/src/app
COPY . .

RUN apt update && apt install clang-9 libclang-dev -y
RUN rustup default nightly-2022-02-04 && rustup component add rust-src && make all
RUN cargo install --path .


FROM python:3.7
COPY --from=builder /usr/src/app/target/release/hellorust /hellorust

CMD ["/hellorust"]
