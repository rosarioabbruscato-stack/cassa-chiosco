#!/usr/bin/env bash
set -euo pipefail

echo "=== Avvio della build locale di Buildozer in Docker ==="

docker run --rm \
  -e BUILDOZER_WARN_ON_ROOT=0 \
  -v "$PWD:/home/user/hostcwd" \
  -w /home/user/hostcwd \
  --entrypoint /bin/bash \
  kivy/buildozer:latest \
  -lc '
    set -euo pipefail
    export DEBIAN_FRONTEND=noninteractive

    apt-get update
    apt-get install -y --no-install-recommends \
      curl ca-certificates unzip zip \
      build-essential pkg-config libssl-dev

    if ! command -v rustup >/dev/null 2>&1; then
      curl --proto "=https" --tlsv1.2 -fsSL https://sh.rustup.rs \
        | sh -s -- -y --profile minimal
    fi
    export PATH="$HOME/.cargo/bin:$PATH"
    rustup --version
    rustc --version
    cargo --version

    SDK="$HOME/.buildozer/android/platform/android-sdk"
    mkdir -p "$SDK/cmdline-tools" "$SDK/licenses"

    if [ ! -x "$SDK/cmdline-tools/latest/bin/sdkmanager" ]; then
      curl -fL --retry 3 \
        -o /tmp/android-commandlinetools.zip \
        https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
      mkdir -p /tmp/android-commandlinetools
      unzip -q /tmp/android-commandlinetools.zip -d /tmp/android-commandlinetools
      mv /tmp/android-commandlinetools/cmdline-tools "$SDK/cmdline-tools/latest"
    fi

    SDKMANAGER="$SDK/cmdline-tools/latest/bin/sdkmanager"
    test -x "$SDKMANAGER"

    printf "%s\n" \
      "8933bad161af4178b1185d1a37fbf41ea5269c55" \
      "d56f5187479451eabf01fb78af6dfcb131a6481e" \
      > "$SDK/licenses/android-sdk-license"

    "$SDKMANAGER" --sdk_root="$SDK" \
      "platform-tools" \
      "platforms;android-36" \
      "build-tools;35.0.0"

    AIDL="$SDK/build-tools/35.0.0/aidl"
    if [ ! -x "$AIDL" ]; then
      echo "ERRORE: AIDL non trovato o non eseguibile: $AIDL" >&2
      exit 1
    fi
    echo "AIDL verificato correttamente in: $AIDL"

    buildozer -v android debug
  '

echo "=== Build completata ==="
ls -lh bin/ || true
