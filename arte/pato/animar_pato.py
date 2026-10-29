"""Esqueleto + animações do pato do Quackroom.

Uso (depois de rodar gerar_pato.py):
    blender --background --factory-startup --python arte/pato/animar_pato.py -- arte/pato [sem-previa]

Entrada:  pato.blend
Saídas:   pato_animado.blend
          ../../jogo/personagens/pato/pato.glb  modelo + esqueleto + animações (para o Godot)
          renders/anim/<animacao>/f_####.png    quadros da prévia

As animações ficam "no lugar": quem move o pato pelo mapa é o código do jogo.
"""
import bpy
import math
import os
import sys
from mathutils import Euler, Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PASTA = os.path.abspath(argv[0] if argv else os.getcwd())
FPS = 24

bpy.ops.wm.open_mainfile(filepath=os.path.join(PASTA, "pato.blend"))
scene = bpy.context.scene
scene.render.fps = FPS
colecao = bpy.data.collections["Pato"]

# tira a montagem da folha de ângulos; o pato passa a ser um objeto só
for o in list(scene.collection.objects):
    if o.name.startswith("Vista") or o.type == "CAMERA":
        bpy.data.objects.remove(o)
bpy.context.view_layer.layer_collection.children["Pato"].exclude = False

# ---------------------------------------------------------------- esqueleto
# O pato olha para -Y. Esquerda do pato = +X (.L), direita = -X (.R).
OSSOS = {
    #  nome       cabeça do osso      ponta do osso       pai
    "raiz":    ((0, 0, 0.00),       (0, 0, 0.25),       None),
    "corpo":   ((0, 0, 0.30),       (0, 0, 1.05),       "raiz"),
    "cabeca":  ((0, -0.06, 1.05),   (0, -0.10, 1.75),   "corpo"),
    "asa.L":   ((0.42, 0.06, 1.05), (0.52, 0.12, 0.45), "corpo"),
    "asa.R":   ((-0.42, 0.06, 1.05), (-0.52, 0.12, 0.45), "corpo"),
    "perna.L": ((0.2, 0, 0.30),     (0.2, 0, 0.05),     "raiz"),
    "perna.R": ((-0.2, 0, 0.30),    (-0.2, 0, 0.05),    "raiz"),
    "pe.L":    ((0.2, 0, 0.05),     (0.2, -0.22, 0.03), "perna.L"),
    "pe.R":    ((-0.2, 0, 0.05),    (-0.2, -0.22, 0.03), "perna.R"),
}

dados_esq = bpy.data.armatures.new("EsqueletoPato")
esq = bpy.data.objects.new("Esqueleto", dados_esq)
colecao.objects.link(esq)
bpy.context.view_layer.objects.active = esq
esq.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for nome, (cabeca, ponta, pai) in OSSOS.items():
    b = dados_esq.edit_bones.new(nome)
    b.head, b.tail = cabeca, ponta
    if pai:
        b.parent = dados_esq.edit_bones[pai]
bpy.ops.object.mode_set(mode="OBJECT")


def prender_ao_osso(o, osso):
    """Peça rígida que segue um osso, sem sair do lugar na pose de descanso."""
    b = dados_esq.bones[osso]
    matriz_osso = esq.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))
    o.parent = esq
    o.parent_type = "BONE"
    o.parent_bone = osso
    o.matrix_parent_inverse = matriz_osso.inverted()


# corpo + pescoço + cabeça são uma malha só: o pescoço dobra com pesos suaves
corpo = bpy.data.objects["Corpo"]
grupo_corpo = corpo.vertex_groups.new(name="corpo")
grupo_cabeca = corpo.vertex_groups.new(name="cabeca")
for v in corpo.data.vertices:
    t = max(0.0, min(1.0, (v.co.z - 1.02) / 0.30))
    peso = t * t * (3 - 2 * t)
    grupo_cabeca.add([v.index], peso, "REPLACE")
    grupo_corpo.add([v.index], 1.0 - peso, "REPLACE")
corpo.modifiers.remove(corpo.modifiers["Suave"])          # o esqueleto tem que vir antes da subdivisão
mod_esq = corpo.modifiers.new("Esqueleto", "ARMATURE")
mod_esq.object = esq
sub = corpo.modifiers.new("Suave", "SUBSURF")
sub.levels = sub.render_levels = 2
corpo.parent = esq

for o in list(colecao.objects):
    if o in (esq, corpo):
        continue
    lado = "L" if o.matrix_world.translation.x > 0 else "R"
    if o.name.startswith(("Olho", "BrilhoOlho", "Bico", "Chapeu", "Costura")):
        prender_ao_osso(o, "cabeca")
    elif o.name.startswith(("Asa", "Abobora", "Alca")):
        prender_ao_osso(o, f"asa.{lado}")
    elif o.name.startswith("Perna"):
        prender_ao_osso(o, f"perna.{lado}")
    elif o.name.startswith("Pe."):
        prender_ao_osso(o, f"pe.{lado}")
    else:                                                   # cachecol e rabo
        prender_ao_osso(o, "corpo")

# ---------------------------------------------------------------- utilitários de pose
for pb in esq.pose.bones:
    pb.rotation_mode = "QUATERNION"


def posar(nome, rot=(0, 0, 0), loc=(0, 0, 0), escala=(1, 1, 1)):
    """rot (graus) e loc em eixos do mundo; escala nos eixos do osso (Y = comprimento)."""
    pb = esq.pose.bones[nome]
    q = dados_esq.bones[nome].matrix_local.to_quaternion()
    giro = Euler([math.radians(a) for a in rot], "XYZ").to_quaternion()
    pb.rotation_quaternion = q.inverted() @ giro @ q
    pb.location = q.inverted() @ Vector(loc)
    pb.scale = escala


def chave(quadro, poses):
    """Grava todos os ossos no quadro; osso não citado volta para o descanso."""
    for nome in OSSOS:
        posar(nome, **poses.get(nome, {}))
        pb = esq.pose.bones[nome]
        for prop in ("rotation_quaternion", "location", "scale"):
            pb.keyframe_insert(prop, frame=quadro, group=nome)


esq.animation_data_create()
ANIMACOES = []  # (nome, último quadro, repete?)


def nova_animacao(nome, ultimo_quadro, repete=True):
    acao = bpy.data.actions.new(nome)
    acao.use_fake_user = True
    esq.animation_data.action = acao
    ANIMACOES.append((nome, ultimo_quadro, repete))
    return acao


def fechar_animacao(acao, ultimo_quadro, repete):
    acao.use_frame_range = True
    acao.frame_start, acao.frame_end = 0, ultimo_quadro
    acao.use_cyclic = repete


def abrir_asas(graus_l, graus_r=None):
    """Asas para fora (positivo) ou para dentro (negativo)."""
    graus_r = graus_l if graus_r is None else graus_r
    return {"asa.L": dict(rot=(0, -graus_l, 0)), "asa.R": dict(rot=(0, graus_r, 0))}


# ---------------------------------------------------------------- parado (respira e olha em volta)
acao = nova_animacao("parado", 48)
for q in range(0, 49, 6):
    p = q / 48
    s = math.sin(2 * math.pi * p)
    poses = {
        "corpo": dict(escala=(1 - 0.01 * s, 1 + 0.02 * s, 1 - 0.01 * s)),
        "cabeca": dict(rot=(2 * math.sin(4 * math.pi * p), 0, 8 * s)),
        **abrir_asas(3 + 2 * s),
    }
    chave(q, poses)
fechar_animacao(acao, 48, True)


# ---------------------------------------------------------------- andar (4 direções, gingado de pato)
def passo(p, amplitude, altura):
    """Uma perna num ciclo: apoio (0–0.5) empurra o chão; balanço (0.5–1) levanta e volta."""
    if p < 0.5:
        return -amplitude + 2 * amplitude * (p / 0.5), 0.0
    s = (p - 0.5) / 0.5
    return amplitude - 2 * amplitude * s, altura * math.sin(math.pi * s)


def andar(nome, eixo, sentido, inclinacao):
    """eixo 0 = passada para frente/trás, 1 = passada de lado; inclinacao = (x, y) do corpo."""
    acao = nova_animacao(nome, 24)
    amplitude = 24 if eixo == 0 else 14
    altura = 0.07
    for q in range(0, 25, 3):
        p = q / 24
        poses = {}
        for lado, fase in (("L", 0.0), ("R", 0.5)):
            ang, sobe = passo((p + fase) % 1.0, amplitude, altura)
            rot = [0.0, 0.0, 0.0]
            rot[eixo] = ang * sentido
            poses[f"perna.{lado}"] = dict(rot=tuple(rot), loc=(0, 0, sobe))
            poses[f"pe.{lado}"] = dict(rot=(25 * sobe / altura, 0, 0))   # ponta do pé cai ao levantar
        ginga = math.sin(2 * math.pi * p)          # +1: apoiado na perna esquerda
        poses["corpo"] = dict(
            rot=(inclinacao[0], 7 * ginga + inclinacao[1], 4 * math.cos(2 * math.pi * p)),
            loc=(0, 0, 0.025 * abs(ginga)),
        )
        poses["cabeca"] = dict(rot=(3 * math.sin(4 * math.pi * p), -4 * ginga, 0))
        poses.update(abrir_asas(6 + 8 * max(0.0, -ginga), 6 + 8 * max(0.0, ginga)))
        chave(q, poses)
    fechar_animacao(acao, 24, True)


andar("andar_frente", 0, 1, (5, 0))
andar("andar_tras", 0, -1, (-4, 0))
andar("andar_esquerda", 1, 1, (0, 4))
andar("andar_direita", 1, -1, (0, -4))

# ---------------------------------------------------------------- agachar (pose baixa, andando escondido)
acao = nova_animacao("agachar", 24)
for q in range(0, 25, 6):
    s = math.sin(2 * math.pi * q / 24)
    chave(q, {
        "corpo": dict(rot=(8, 0, 0), loc=(0, 0, -0.14), escala=(1.07, 0.88 + 0.012 * s, 1.07)),
        "cabeca": dict(rot=(10, 0, 0), loc=(0, 0, -0.03)),
        **abrir_asas(-3),
    })
fechar_animacao(acao, 24, True)

# ---------------------------------------------------------------- pular (prepara, bate asas, aterrissa)
acao = nova_animacao("pular", 28, repete=False)
pernas_penduradas = lambda graus: {
    "perna.L": dict(rot=(graus, 0, 0)), "perna.R": dict(rot=(graus, 0, 0)),
}
pes_apontados = lambda graus: {"pe.L": dict(rot=(graus, 0, 0)), "pe.R": dict(rot=(graus, 0, 0))}
chave(0, {})
chave(4, {"corpo": dict(loc=(0, 0, -0.10), escala=(1.10, 0.84, 1.10)),
          "cabeca": dict(rot=(8, 0, 0)), **abrir_asas(25)})
chave(8, {"corpo": dict(escala=(0.93, 1.12, 0.93)), "cabeca": dict(rot=(-6, 0, 0)),
          **abrir_asas(60), **pernas_penduradas(25), **pes_apontados(30)})
chave(12, {"cabeca": dict(rot=(-3, 0, 0)), **abrir_asas(15), **pernas_penduradas(15), **pes_apontados(20)})
chave(16, {**abrir_asas(55), **pernas_penduradas(5), **pes_apontados(10)})
chave(20, {**abrir_asas(20), **pernas_penduradas(-10)})
chave(23, {"corpo": dict(loc=(0, 0, -0.10), escala=(1.12, 0.84, 1.12)),
           "cabeca": dict(rot=(10, 0, 0)), **abrir_asas(35)})
chave(28, {})
fechar_animacao(acao, 28, False)

# ---------------------------------------------------------------- grasnar (estica o pescoço e abre as asas)
acao = nova_animacao("grasnar", 14, repete=False)
chave(0, {})
chave(3, {"corpo": dict(escala=(1.07, 0.9, 1.07)), "cabeca": dict(rot=(12, 0, 0)), **abrir_asas(10)})
chave(6, {"corpo": dict(escala=(0.95, 1.1, 0.95)), "cabeca": dict(rot=(-22, 0, 0)), **abrir_asas(40)})
chave(14, {})
fechar_animacao(acao, 14, False)

esq.animation_data.action = bpy.data.actions["parado"]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PASTA, "pato_animado.blend"))

# ---------------------------------------------------------------- exporta para o Godot
GLB = os.path.join(os.path.dirname(os.path.dirname(PASTA)), "jogo", "personagens", "pato", "pato.glb")
os.makedirs(os.path.dirname(GLB), exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
for o in colecao.objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = esq
bpy.ops.export_scene.gltf(
    filepath=GLB,
    export_format="GLB",
    use_selection=True,
    export_apply=True,
    export_animations=True,
    export_animation_mode="ACTIONS",
)

if "sem-previa" in argv:
    print("TUDO_OK sem prévia", [a[0] for a in ANIMACOES])
    sys.exit(0)

# ---------------------------------------------------------------- prévia em vídeo
alvo =bpy.data.objects.new("AlvoCamera", None)
alvo.location = (0, 0, 1.15)
scene.collection.objects.link(alvo)
cam = bpy.data.objects.new("CameraPrevia", bpy.data.cameras.new("CameraPrevia"))
cam.location = (3.3, -4.8, 2.0)
cam.data.lens = 35
mira = cam.constraints.new("TRACK_TO")
mira.target = alvo
mira.track_axis = "TRACK_NEGATIVE_Z"
mira.up_axis = "UP_Y"
scene.collection.objects.link(cam)
scene.camera = cam

chao_mat = bpy.data.materials.new("Chao")
chao_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.03, 0.025, 0.05, 1)
bpy.ops.mesh.primitive_plane_add(size=30)
chao = bpy.context.active_object
chao.name = "Chao"
chao.data.materials.append(chao_mat)

texto_dados = bpy.data.curves.new("Rotulo", "FONT")
texto_dados.size = 0.09
rotulo = bpy.data.objects.new("Rotulo", texto_dados)
rotulo_mat = bpy.data.materials.new("RotuloMat")
rotulo_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1, 1, 1, 1)
rotulo_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 1.0
texto_dados.materials.append(rotulo_mat)
rotulo.parent = cam
rotulo.location = (-0.95, 0.47, -2.0)
scene.collection.objects.link(rotulo)

# pulo: só na prévia o pato sobe de verdade (no jogo quem sobe é a física)
elevador = bpy.data.objects.new("ElevadorPrevia", None)
scene.collection.objects.link(elevador)
esq.parent = elevador

ROTULOS = {
    "parado": "parado", "andar_frente": "andar para frente", "andar_tras": "andar para trás",
    "andar_esquerda": "andar para a esquerda", "andar_direita": "andar para a direita",
    "agachar": "agachar", "pular": "pular", "grasnar": "grasnar",
}
scene.render.resolution_x, scene.render.resolution_y = 960, 540
scene.eevee.taa_render_samples = 24
scene.render.image_settings.file_format = "PNG"
for nome, ultimo, repete in ANIMACOES:
    esq.animation_data.action = bpy.data.actions[nome]
    texto_dados.body = ROTULOS[nome]
    elevador.animation_data_clear()
    elevador.location.z = 0
    fim = ultimo - 1 if repete else ultimo + 8          # loop: o último quadro repete o primeiro
    if nome == "pular":
        for quadro, z in ((0, 0), (6, 0), (12, 0.7), (18, 0.25), (21, 0), (fim, 0)):
            elevador.location.z = z
            elevador.keyframe_insert("location", index=2, frame=quadro)
    scene.frame_start, scene.frame_end = 0, fim
    scene.render.filepath = os.path.join(PASTA, "renders", "anim", nome, "f_")
    bpy.ops.render.render(animation=True)
    print("ANIM_OK", nome)

print("TUDO_OK", [a[0] for a in ANIMACOES])
