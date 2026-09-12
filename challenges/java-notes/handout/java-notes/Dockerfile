FROM maven:3.9-eclipse-temurin-11@sha256:c46b31057b9eb90e3ec855f6db35fc99108cadcdd1a03336bfb6516ba12212ef AS build
WORKDIR /build
COPY src/pom.xml .
RUN mvn -q -e -B dependency:go-offline
COPY src/src ./src
RUN mvn -q -e -B package

FROM eclipse-temurin:11-jre@sha256:e9aa18936347d6496697b2b2698b7ec1e228ee3d8d0871302d6a8ccd0ce8db38
WORKDIR /app

COPY flag /flag.txt
RUN chmod 644 /flag.txt

COPY --from=build /build/target/javanotes.jar /app/javanotes.jar

RUN useradd -m -u 10001 ctf
USER ctf

ENV PORT=8080
EXPOSE 8080
CMD ["java", "-jar", "/app/javanotes.jar"]
