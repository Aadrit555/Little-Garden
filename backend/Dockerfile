# Real image: bundles Montreal Forced Aligner + the real German acoustic
# model + dictionary INTO the image at build time, so anyone who runs
# this container gets working Speaking scoring out of the box — no
# manual MFA install needed on their end. MFA has heavy binary deps
# (Kaldi etc), so it's installed via conda (the officially supported
# install path for MFA), not pip.
#
# NOTE: building this image needs real internet access to conda-forge
# and the MFA model hosts (huggingface). That's normal for a Docker
# build on any real machine/CI runner — just flagging it here since
# this exact build was written and inspected in a network-restricted
# sandbox that couldn't run `docker build` itself to verify it live.
FROM condaforge/miniforge3:latest

# ffmpeg required for speaking audio conversion (webm -> wav)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Real MFA install via conda-forge (MFA's own documented install path),
# into the base conda env so `mfa` is directly on PATH — no env
# activation gymnastics needed in later RUN/CMD layers.
RUN conda install -y -n base -c conda-forge montreal-forced-aligner python=3.12 \
    && conda clean -afy

# Real German acoustic model + pronunciation dictionary, downloaded
# once at build time and baked into the image — every container start
# has them ready immediately, no runtime download, no missing-model error.
RUN mfa model download acoustic german_mfa \
    && mfa model download dictionary german_mfa

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# gunicorn + uvicorn workers for real production serving, not --reload dev server
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "180"]
