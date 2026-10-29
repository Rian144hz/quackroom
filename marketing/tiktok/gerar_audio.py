"""Narração + trilha + efeitos do vídeo do Quackroom, e montagem final do MP4.

Tudo é gerado aqui: a voz vem do Piper (TTS offline, voz pt_BR "faber") e a música e
os efeitos são sintetizados — nenhum sample de terceiros.

Uso, a partir da raiz do projeto (depois de gerar_video.py, que deixa os quadros prontos):
    python3 marketing/tiktok/gerar_audio.py sem-voz   # versão principal: trilha + efeitos
    python3 marketing/tiktok/gerar_audio.py           # versão narrada

Saídas em marketing/tiktok/:
    quackroom_tiktok.mp4          trilha + efeitos (sem-voz)
    quackroom_tiktok_mudo.mp4     o mesmo vídeo sem áudio
    quackroom_tiktok_com_voz.mp4  narração + trilha + efeitos
    narracao/NN.wav               cada fala da narração

Quando uma fala não cabe na cena, a cena ganha uma pausa (o último quadro fica parado)
e todos os efeitos e a música são reposicionados para o novo tempo.
"""
import os
import subprocess
import sys

import numpy as np
from scipy import signal
from scipy.io import wavfile

AQUI = os.path.dirname(os.path.abspath(__file__))
SR = 44100
FPS = 24
rng = np.random.default_rng(7)

PIPER = os.path.expanduser("~/.local/share/piper-tts/venv/bin/piper")
VOZ = os.path.expanduser("~/.local/share/piper-tts/vozes/pt_BR-faber-medium.onnx")

CENAS = [("gancho", 84), ("titulo", 108), ("historia", 144), ("sonar", 168), ("sonambulo", 168),
         ("patinhos", 144), ("coop", 120), ("recrutamento", 168), ("final", 84)]

# (cena, quadro em que a fala quer começar, texto). Grafias ajustadas para a pronúncia do Piper.
FALAS = [
    ("gancho", 30, "E se fazer barulho fosse o único jeito de enxergar?"),
    ("titulo", 6, "Quack rum. Terror cooperativo, de um a quatro jogadores, online."),
    ("historia", 4, "Uma ninhada de patinhos se perdeu dentro de uma casa."),
    ("historia", 74, "Pra um pato, cada cômodo é... gigante."),
    ("sonar", 6, "A casa tá no escuro total."),
    ("sonar", 60, "O quack é o seu sonar."),
    ("sonar", 116, "Mas todo barulho... acorda o dono da casa."),
    ("sonambulo", 6, "O dono da casa é sonâmbulo."),
    ("sonambulo", 108, "Se ele acordar, a luz acende. E aí, já era."),
    ("patinhos", 14, "Os patinhos seguem o último quack que ouvirem."),
    ("patinhos", 86, "Leve todos de volta pro ninho!"),
    ("coop", 4, "Jogue com até quatro amigos online."),
    ("coop", 66, "Alguém tem que grasnar... e virar a isca."),
    ("recrutamento", 4, "Tô criando o Quack rum, e procuro gente pro time!"),
    ("recrutamento", 44, "Arte três dê, som, programação em Godô, e lével dizáin."),
    ("recrutamento", 124, "Comenta quack, que eu te chamo!"),
    ("final", 6, "Quack rum. Faça barulho... se tiver coragem."),
]


SEM_VOZ = "sem-voz" in sys.argv          # python3 gerar_audio.py sem-voz: só trilha e efeitos, sem pausas
if SEM_VOZ:
    FALAS = []


def sintetizar(texto, caminho):
    subprocess.run([PIPER, "-m", VOZ, "-f", caminho, "--length-scale", "0.9", "--sentence-silence", "0.15"],
                   input=texto.encode(), check=True, capture_output=True)
    taxa, dados = wavfile.read(caminho)
    voz = dados.astype(float) / 32768
    voz = signal.resample_poly(voz, SR, taxa)
    falando = np.flatnonzero(np.abs(voz) > 0.02)            # corta o silêncio das pontas
    return voz[max(0, falando[0] - 400):falando[-1] + 2000]


os.makedirs(os.path.join(AQUI, "narracao"), exist_ok=True)
vozes = [sintetizar(texto, os.path.join(AQUI, "narracao", f"{i:02d}.wav")) for i, (_, _, texto) in enumerate(FALAS)]

# Agenda: cada fala começa no quadro pedido ou logo depois da anterior; a cena estica se precisar.
INICIO, PAUSA, COMECO_FALA = {}, {}, []
relogio, fim_fala = 0.0, 0.0
for nome, quadros in CENAS:
    INICIO[nome] = relogio
    fim_cena = relogio + quadros / FPS
    precisa = fim_cena
    for (cena, quadro, _), voz in zip(FALAS, vozes):
        if cena != nome:
            continue
        comeco = max(relogio + quadro / FPS, fim_fala + 0.15)
        fim_fala = comeco + len(voz) / SR
        COMECO_FALA.append(comeco)
        precisa = max(precisa, fim_fala + 0.3)
    PAUSA[nome] = round((precisa - fim_cena) * FPS) / FPS
    relogio = fim_cena + PAUSA[nome]
DURACAO = relogio
FLASH = INICIO["sonambulo"] + 100 / FPS
for (cena, quadro, texto), comeco, voz in zip(FALAS, COMECO_FALA, vozes):
    print(f"  {comeco:5.2f}-{comeco + len(voz) / SR:5.2f}s  {cena:12s} {texto}")
print("PAUSAS", {k: round(v, 2) for k, v in PAUSA.items() if v}, "DURACAO", round(DURACAO, 2))

tamanho = int(SR * (DURACAO + 3))
BUS = {"musica": np.zeros((tamanho, 2)), "efeitos": np.zeros((tamanho, 2)), "voz": np.zeros((tamanho, 2))}


def em(cena, quadro):
    return INICIO[cena] + quadro / FPS


def tempo(dur):
    return np.arange(int(SR * dur)) / SR


def normal(x):
    pico = np.max(np.abs(x))
    return x / pico if pico else x


def filtro(x, tipo, freq, ordem=2):
    return signal.sosfilt(signal.butter(ordem, freq, btype=tipo, fs=SR, output="sos"), x)


def ressonancia(x, freq, q):
    b, a = signal.iirpeak(freq, q, fs=SR)
    return signal.lfilter(b, a, x)


def fase(freqs):
    return 2 * np.pi * np.cumsum(freqs) / SR


def colocar(som, instante, ganho=1.0, pan=0.0, bus="efeitos"):
    """Mixa um som (mono com pan, ou estéreo) a partir do instante em segundos."""
    mix = BUS[bus]
    if som.ndim == 1:
        angulo = (pan + 1) * np.pi / 4
        som = np.stack([som * np.cos(angulo), som * np.sin(angulo)], axis=1) * np.sqrt(2)
    i = int(instante * SR)
    j = min(len(mix), i + len(som))
    if j > i:
        mix[i:j] += som[:j - i] * ganho


# ---------------------------------------------------------------- efeitos
def quack(tom=1.0):
    t = tempo(0.26)
    f = 470 * tom * np.exp(-t * 2.4)                       # o tom cai: "quaaack"
    onda = (np.mod(fase(f) / (2 * np.pi), 1.0) < 0.28) * 2.0 - 1   # pulso estreito = som anasalado
    onda *= 1 + 0.4 * np.sin(2 * np.pi * 58 * t)           # aspereza de pato
    onda += 0.12 * rng.standard_normal(len(t))
    voz = (ressonancia(onda, 1150 * tom, 5) + 0.6 * ressonancia(onda, 2500 * tom, 7)
           + 0.5 * filtro(onda, "low", 700))
    env = np.minimum(1, t / 0.012) * np.exp(-np.maximum(0, t - 0.07) * 13)
    return normal(voz * env)


def ping(freq=1150):
    """Ping de sonar com ecos alternando entre os lados."""
    t = tempo(1.6)
    s = np.sin(2 * np.pi * freq * t * (1 - 0.03 * t)) * np.exp(-t * 3.0) * np.minimum(1, t / 0.004)
    s += 0.3 * np.sin(2 * np.pi * freq * 2.01 * t) * np.exp(-t * 6)
    est = np.zeros((len(s) + int(SR * 0.7), 2))
    for atraso, ganho, pan in ((0, 1.0, 0), (0.2, 0.45, -0.7), (0.4, 0.25, 0.7), (0.6, 0.12, -0.4)):
        i = int(atraso * SR)
        angulo = (pan + 1) * np.pi / 4
        est[i:i + len(s), 0] += s * ganho * np.cos(angulo) * np.sqrt(2)
        est[i:i + len(s), 1] += s * ganho * np.sin(angulo) * np.sqrt(2)
    return est / np.max(np.abs(est))


def impacto(dur=1.8, grave=38, agudo=95):
    t = tempo(dur)
    f = grave + (agudo - grave) * np.exp(-t * 6)
    corpo = np.sin(fase(f)) * np.exp(-t * 2.2)
    estalo = filtro(rng.standard_normal(len(t)), "low", 900) * np.exp(-t * 12) * 0.6
    return normal(np.tanh((corpo + estalo) * 1.6))


def whoosh(dur=0.5):
    t = tempo(dur)
    return normal(filtro(rng.standard_normal(len(t)), "band", [500, 4000]) * np.sin(np.pi * t / dur) ** 2)


def pop(tom=1.0):
    t = tempo(0.09)
    return normal(np.sin(fase((700 + 900 * t / 0.09) * tom)) * np.exp(-t * 40) * np.minimum(1, t / 0.002))


def bip(freq, dur=0.13):
    t = tempo(dur)
    onda = np.sign(np.sin(2 * np.pi * freq * t)) * 0.4 + np.sin(2 * np.pi * freq * t)
    return normal(filtro(onda, "low", 3000) * np.minimum(1, t / 0.005) * np.minimum(1, (dur - t) / 0.02))


def clique():
    t = tempo(0.05)
    return normal(filtro(rng.standard_normal(len(t)), "high", 2000) * np.exp(-t * 300)
                  + 0.6 * np.sin(2 * np.pi * 180 * t) * np.exp(-t * 80))


def brilho_flash(dur=1.6):
    t = tempo(dur)
    return normal(filtro(rng.standard_normal(len(t)), "high", 5000) * np.exp(-t * 2.5) * np.minimum(1, t / 0.01))


def ronco(dur):
    """Inspira roncando, expira soprando, num ciclo de 2.4 s."""
    t = tempo(dur)
    ciclo = np.mod(t, 2.4)
    inspira = (ciclo < 1.1) * np.sin(np.pi * np.clip(ciclo / 1.1, 0, 1))
    expira = ((ciclo >= 1.1) & (ciclo < 2.1)) * np.sin(np.pi * np.clip((ciclo - 1.1) / 1.0, 0, 1)) * 0.45
    ruido = rng.standard_normal(len(t))
    palato = filtro(ruido, "low", 380) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 32 * t)))
    sopro = filtro(ruido, "band", [300, 1500])
    return normal(palato * inspira + 0.6 * sopro * expira)


def batida():
    t = tempo(0.45)
    lub = np.sin(2 * np.pi * 55 * t) * np.exp(-t * 16)
    dub = np.zeros_like(t)
    i = int(0.17 * SR)
    dub[i:] = 0.6 * np.sin(2 * np.pi * 60 * t[:-i]) * np.exp(-t[:-i] * 18)
    return normal(lub + dub)


def piu():
    d = 0.1 + 0.04 * rng.random()
    t = tempo(d)
    base = 2500 + 500 * rng.random()
    s = np.sin(fase(base + 900 * t / d)) * np.sin(np.pi * t / d) ** 1.5
    return normal(s + 0.2 * np.sin(fase(2 * (base + 900 * t / d))))


def bumbo():
    t = tempo(0.35)
    return normal(np.sin(fase(48 + 110 * np.exp(-t * 30))) * np.exp(-t * 9))


def chimbal():
    t = tempo(0.06)
    return normal(filtro(rng.standard_normal(len(t)), "high", 7000) * np.exp(-t * 70))


# ---------------------------------------------------------------- música
def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def pad(dur, notas, corte=750):
    """Drone sombrio: serras desafinadas, filtradas, respirando devagar."""
    t = tempo(dur)
    s = np.zeros(len(t))
    for f in notas:
        for desafino in (-0.0015, 0.0, 0.0013):
            ph = 2 * np.pi * f * (1 + desafino) * t + rng.random() * 6.28
            s += 2 * np.mod(ph / (2 * np.pi), 1.0) - 1
    s = filtro(s, "low", corte, 2)
    return normal(s) * (0.78 + 0.22 * np.sin(2 * np.pi * 0.13 * t))


def corda(freq, dur=1.6, brilho=0.5):
    """Karplus-Strong: som de corda dedilhada."""
    n = int(SR / freq)
    excitacao = np.zeros(int(SR * dur))
    excitacao[:n] = rng.uniform(-1, 1, n)
    a = np.zeros(n + 2)
    a[0], a[n], a[n + 1] = 1.0, -0.498 * (1 + brilho * 0.002), -0.498 * (1 - brilho * 0.002)
    return normal(signal.lfilter([1.0], a, excitacao))


def baixo(freq, dur):
    t = tempo(dur)
    s = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * 2 * freq * t)
    return normal(s * np.minimum(1, t / 0.02) * np.exp(-t * 1.2))


def envelope(n, sobe, desce):
    env = np.ones(n)
    a, b = int(sobe * SR), int(desce * SR)
    if a:
        env[:a] = np.linspace(0, 1, a)
    if b:
        env[-b:] *= np.linspace(1, 0, b)
    return env


# ---------------------------------------------------------------- montagem
# drone de suspense até o flash (corta seco quando a luz acende)
d = FLASH - 1.0
som = pad(d, [midi(45), midi(33), midi(52), midi(48)])
colocar(som * envelope(len(som), 2.5, 0.02), 1.0, 0.16, bus="musica")

# gancho
colocar(quack(), em("gancho", 3), 0.85)
colocar(ping(), em("gancho", 5), 0.5)
colocar(ping(1000), em("gancho", 14), 0.25)
colocar(whoosh(0.6), em("gancho", 33), 0.2)

# título
colocar(whoosh(0.5), em("titulo", 0) - 0.3, 0.3)
colocar(impacto(1.4, 45, 110), em("titulo", 4), 0.55)
for q in (4, 40, 76):
    colocar(ping(900), em("titulo", q), 0.18)
for q in (16, 26):
    colocar(pop(), em("titulo", q), 0.18)

# história
for q in (14, 80):
    colocar(quack(1.03), em("historia", q), 0.75)
for q in (18, 84):
    colocar(ping(), em("historia", q), 0.4)
for q in (4, 74):
    colocar(pop(0.9), em("historia", q), 0.15)
colocar(impacto(2.2), em("historia", 86), 0.8)

# sonar
for q in (4, 62, 116):
    colocar(pop(0.9), em("sonar", q), 0.15)
for q in (50, 98):
    colocar(quack(0.97), em("sonar", q), 0.8)
for q in (54, 102):
    colocar(ping(1250), em("sonar", q), 0.5)
colocar(impacto(1.8, 34, 80), em("sonar", 132), 0.6)

# sonâmbulo: ronco + coração acelerando + barra de sono + flash
colocar(ronco(100 / FPS), em("sonambulo", 0), 0.32, pan=0.1)
instante, intervalo = em("sonambulo", 0) + 0.3, 0.85
while instante < FLASH - 0.15:
    colocar(batida(), instante, 0.55)
    instante += intervalo
    intervalo = max(0.36, intervalo * 0.9)
for q in (30, 62, 94):
    colocar(quack(1.05), em("sonambulo", q), 0.8, pan=0.15)
colocar(bip(554), em("sonambulo", 34), 0.22)
colocar(bip(659), em("sonambulo", 66), 0.24)
for k in range(3):
    colocar(bip(880, 0.09), em("sonambulo", 98) + 0.11 * k, 0.28)
colocar(clique(), FLASH - 0.05, 0.6)
colocar(impacto(2.4, 30, 120), FLASH, 1.0)
colocar(brilho_flash(), FLASH, 0.25)
cluster = normal(pad(1.6, [midi(33), midi(34), midi(40)], corte=500))
colocar(cluster * envelope(len(cluster), 0.25, 0.9), em("sonambulo", 128), 0.45, bus="musica")

# patinhos (parte mais leve começa aqui)
colocar(whoosh(0.7), INICIO["patinhos"] - 0.4, 0.25)
colocar(quack(), em("patinhos", 6), 0.75, pan=-0.4)
colocar(ping(), em("patinhos", 6), 0.35)
instante = INICIO["patinhos"] + 0.6
while instante < INICIO["coop"] - 0.2:
    colocar(piu(), instante, 0.16, pan=-0.5 + 0.6 * rng.random())
    instante += 0.22 + 0.3 * rng.random()
for q in (14, 86):
    colocar(pop(1.1), em("patinhos", q), 0.15)

# co-op
colocar(pop(), em("coop", 4), 0.15)
colocar(quack(0.94), em("coop", 62), 0.8, pan=-0.2)
colocar(ping(), em("coop", 64), 0.4)
colocar(impacto(1.2, 50, 120), em("coop", 84), 0.45)

# recrutamento
for q in (0, 56, 112):
    colocar(ping(950), em("recrutamento", q), 0.15)
colocar(impacto(1.2, 50, 130), em("recrutamento", 8), 0.4)
for k, q in enumerate((44, 53, 62, 71)):
    colocar(pop(1 + 0.15 * k), em("recrutamento", q), 0.2)
colocar(quack(), em("recrutamento", 124), 0.8)
colocar(impacto(1.2, 50, 130), em("recrutamento", 124), 0.4)

# final
colocar(whoosh(0.4), em("final", 2), 0.3)
colocar(bumbo(), em("final", 21), 0.4)
colocar(ping(), em("final", 22), 0.35)
colocar(impacto(1.4, 45, 110), em("final", 6), 0.45)
for q in (20, 32):
    colocar(pop(), em("final", q), 0.15)

# arpejo animado (Am – F – C – G) dos patinhos até o fim, com batida no recrutamento
BPM = 112
colcheia = 60 / BPM / 2
acordes = [(57, [57, 60, 64, 69]), (53, [53, 57, 60, 65]), (48, [60, 64, 67, 72]), (55, [55, 59, 62, 67])]
padrao = [0, 1, 2, 3, 2, 1, 2, 3]
instante, passo = INICIO["patinhos"], 0
while instante < INICIO["final"] - 0.05:
    raiz, notas = acordes[(passo // 8) % 4]
    colocar(corda(midi(notas[padrao[passo % 8]]), 1.2), instante, 0.2, pan=-0.3 + 0.6 * (passo % 2), bus="musica")
    if passo % 8 == 0:
        colocar(baixo(midi(raiz - 24), colcheia * 8), instante, 0.22, bus="musica")
    if instante >= INICIO["recrutamento"]:
        if passo % 4 == 0:
            colocar(bumbo(), instante, 0.32, bus="musica")
        if passo % 2 == 1:
            colocar(chimbal(), instante, 0.06, pan=0.3, bus="musica")
    instante += colcheia
    passo += 1
for k, n in enumerate((45, 57, 64, 69, 72)):                 # acorde final de Lá menor
    colocar(corda(midi(n), 3.4, 0.2), INICIO["final"] + 0.03 * k, 0.2, pan=-0.4 + 0.2 * k, bus="musica")
som = pad(3.5, [midi(45), midi(57), midi(64)], corte=1200)
colocar(som * envelope(len(som), 0.3, 1.5), INICIO["final"], 0.12, bus="musica")

# ---------------------------------------------------------------- narração
for comeco, voz in zip(COMECO_FALA, vozes):
    voz = filtro(voz, "high", 90)
    voz = np.tanh(2.0 * normal(voz)) / np.tanh(2.0)          # compressão leve: voz sempre na frente
    colocar(voz, comeco, 0.95, bus="voz")

# ---------------------------------------------------------------- master (música abaixa quando a voz fala)
from scipy.ndimage import maximum_filter1d, uniform_filter1d

falando = (np.abs(BUS["voz"]).max(axis=1) > 0.02).astype(float)
falando = uniform_filter1d(maximum_filter1d(falando, int(0.15 * SR)), int(0.25 * SR))
saida = (BUS["musica"] * (1 - 0.65 * falando)[:, None]
         + BUS["efeitos"] * (1 - 0.35 * falando)[:, None]
         + BUS["voz"])[:int(SR * DURACAO)]
saida = np.tanh(saida * 1.3) / np.tanh(1.3)                  # limitador suave
saida = saida / np.max(np.abs(saida)) * 0.89
fim = int(SR * 0.6)
saida[-fim:] *= np.linspace(1, 0, fim)[:, None]
wav = os.path.join(AQUI, "trilha.wav" if SEM_VOZ else "trilha_com_voz.wav")
wavfile.write(wav, SR, (saida * 32767).astype(np.int16))

# ---------------------------------------------------------------- vídeo com as pausas novas
quadros = os.path.join(AQUI, "quadros")
lista = os.path.join(quadros, "lista_final.txt")
with open(lista, "w") as arq:
    for i, (nome, n) in enumerate(CENAS):
        dur = n / FPS + PAUSA[nome]
        filtros = [f"tpad=stop_mode=clone:stop_duration={PAUSA[nome]:.4f}"] if PAUSA[nome] else []
        if i:
            filtros.append("fade=t=in:st=0:d=0.12")
        filtros.append(f"fade=t=out:st={dur - 0.12:.4f}:d=0.12")
        clipe = os.path.join(quadros, f"{i:02d}_{nome}_final.mp4")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-start_number", "0",
                        "-i", os.path.join(quadros, f"{i:02d}_{nome}", "f_%04d.png"), "-vf", ",".join(filtros),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", clipe], check=True)
        arq.write(f"file '{clipe}'\n")
mudo = os.path.join(AQUI, "quackroom_tiktok_mudo.mp4") if SEM_VOZ else os.path.join(quadros, "video_com_pausas.mp4")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista,
                "-c", "copy", "-movflags", "+faststart", mudo], check=True)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", mudo, "-i", wav, "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100",
                "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
                os.path.join(AQUI, "quackroom_tiktok.mp4" if SEM_VOZ else "quackroom_tiktok_com_voz.mp4")],
               check=True)
print("FINAL_OK", round(DURACAO, 2), "s")
