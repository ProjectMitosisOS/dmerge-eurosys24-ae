# Use the official Rust image.
# https://hub.docker.com/_/rust
FROM rust:1.62.1 as builder

# Copy local code to the container image.
WORKDIR /usr/src/app
COPY . .

# Install production dependencies and build a release artifact.
RUN cargo install --path .


FROM scratch
COPY --from=builder /usr/src/app/target/release/hellorust /hellorust

CMD ["/hellorust"]
