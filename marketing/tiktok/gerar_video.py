"""Vídeo de divulgação do Quackroom para TikTok (1080x1920, 24 fps, ~50 s).

Usa o pato animado (arte/pato/pato_animado.blend) e monta cada cena no Blender.

Uso, a partir da raiz do projeto:
    blender --background --factory-startup --python marketing/tiktok/gerar_video.py -- .
    blender ... -- . amostra          # só alguns quadros de cada cena, em baixa resolução
    blender ... -- . <nome_da_cena>   # renderiza só uma cena

Saída: marketing/tiktok/quackroom_tiktok.mp4
"""
import bpy
import bmesh
import math
import os
import subprocess
import sys
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RAIZ = os.path.abspath(argv[0] if argv else os.getcwd())
MODO = argv[1] if len(argv) > 1 else "completo"   # completo | amostra[:cena[:quadro]] | <cena>
SAIDA = os.path.join(RAIZ, "marketing", "tiktok")
FPS = 24

bpy.ops.wm.open_mainfile(filepath=os.path.join(RAIZ, "arte", "pato", "pato_animado.blend"))
scene = bpy.context.scene
scene.render.fps = FPS
scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
scene.render.resolution_percentage = 50 if MODO.startswith("amostra") else 100
scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = 16
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.file_format = "PNG"

CIANO, LARANJA, BRANCO = "7CF3FF", "FF8A1E", "FFFFFF"
ESCURO, VERMELHO, CINZA = "15111F", "FF3B3B", "A49FB8"

col_pato = bpy.data.collections["Pato"]
bpy.context.view_layer.layer_collection.children["Pato"].exclude = True
esq = bpy.data.objects["Esqueleto"]
LUZES = [(o, o.data.energy) for o in scene.objects if o.type == "LIGHT"]
mundo = scene.world
fundo = mundo.node_tree.nodes["Background"]

TITULO = bpy.data.fonts.load("/usr/share/fonts/truetype/lato/Lato-Black.ttf")
NORMAL = bpy.data.fonts.load("/usr/share/fonts/truetype/lato/Lato-Bold.ttf")


# ---------------------------------------------------------------- utilitários gerais
def linear(hexcor):
    h = hexcor.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda x: x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]), 1.0)


def curvas(acao):
    """F-curves de uma action (funciona com as actions em camadas do Blender 4.4+)."""
    if acao is None:
        return []
    resultado = []
    for camada in getattr(acao, "layers", []):
        for faixa in camada.strips:
            for saco in faixa.channelbags:
                resultado.extend(saco.fcurves)
    if not resultado and hasattr(acao, "fcurves"):
        resultado = list(acao.fcurves)
    return resultado


def interpolacao(id_dados, tipo):
    if id_dados.animation_data:
        for fc in curvas(id_dados.animation_data.action):
            for k in fc.keyframe_points:
                k.interpolation = tipo


_emissivos = {}


def emissivo(hexcor, forca=1.0, unico=False):
    chave = (hexcor, forca)
    if chave in _emissivos and not unico:
        return _emissivos[chave]
    m = bpy.data.materials.new(f"Luz_{hexcor}")
    nos = m.node_tree.nodes
    for n in list(nos):
        if n.type != "OUTPUT_MATERIAL":
            nos.remove(n)
    em = nos.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = linear(hexcor)
    em.inputs["Strength"].default_value = forca
    m.node_tree.links.new(em.outputs[0], nos["Material Output"].inputs["Surface"])
    if not unico:
        _emissivos[chave] = m
    return m


def fosco(hexcor, rugosidade=0.85):
    m = bpy.data.materials.new(f"Fosco_{hexcor}")
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = linear(hexcor)
    bsdf.inputs["Roughness"].default_value = rugosidade
    return m


def malha(nome, bm, mat, colecao, loc=(0, 0, 0), rot=(0, 0, 0), suave=False, subdiv=0):
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = suave
    me.materials.append(mat)
    o = bpy.data.objects.new(nome, me)
    colecao.objects.link(o)
    o.location = loc
    o.rotation_euler = [math.radians(a) for a in rot]
    if subdiv:
        s = o.modifiers.new("Suave", "SUBSURF")
        s.levels = s.render_levels = subdiv
    return o


def bm_esfera(raios, seg=12, aneis=8):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=aneis, radius=1.0)
    bmesh.ops.scale(bm, vec=raios, verts=bm.verts)
    return bm


def bm_caixa(dims):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=dims, verts=bm.verts)
    return bm


def bm_cilindro(raio, altura, seg=12, raio_topo=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=raio,
                          radius2=raio if raio_topo is None else raio_topo, depth=altura)
    return bm


def bm_anel(espessura=0.02, seg=72):
    """Anel fino de raio 1 no plano XY (a onda do sonar)."""
    bm = bmesh.new()
    dentro, fora = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        dentro.append(bm.verts.new((math.cos(a) * (1 - espessura), math.sin(a) * (1 - espessura), 0)))
        fora.append(bm.verts.new((math.cos(a) * (1 + espessura), math.sin(a) * (1 + espessura), 0)))
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((dentro[i], fora[i], fora[j], dentro[j]))
    return bm


def bm_retangulo(largura, altura, ancora_esquerda=False):
    bm = bmesh.new()
    x0 = 0.0 if ancora_esquerda else -largura / 2
    vs = [bm.verts.new((x0 + dx, dy, 0)) for dx, dy in
          ((0, -altura / 2), (largura, -altura / 2), (largura, altura / 2), (0, altura / 2))]
    bm.faces.new(vs)
    return bm


# ---------------------------------------------------------------- pato: tinta por instância
def tingir(mat):
    """Multiplica a cor das penas pela propriedade 'tinta' de quem instancia o pato."""
    nt = mat.node_tree
    entrada = nt.nodes["Principled BSDF"].inputs["Base Color"]
    if entrada.links:
        origem = entrada.links[0].from_socket
    else:
        rgb = nt.nodes.new("ShaderNodeRGB")
        rgb.outputs[0].default_value = entrada.default_value
        origem = rgb.outputs[0]
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_type = "INSTANCER"
    attr.attribute_name = "tinta"
    mult = nt.nodes.new("ShaderNodeVectorMath")
    mult.operation = "MULTIPLY"
    nt.links.new(origem, mult.inputs[0])
    nt.links.new(attr.outputs["Vector"], mult.inputs[1])
    nt.links.new(mult.outputs["Vector"], entrada)


tingir(bpy.data.materials["PenasCorpo"])
tingir(bpy.data.materials["Penas"])

# animações em loop repetem sozinhas na timeline
for nome in ("parado", "andar_frente", "andar_tras", "andar_esquerda", "andar_direita", "agachar"):
    for fc in curvas(bpy.data.actions[nome]):
        fc.modifiers.new("CYCLES")


def posar(nome, rot=(0, 0, 0), loc=(0, 0, 0), escala=(1, 1, 1)):
    pb = esq.pose.bones[nome]
    q = esq.data.bones[nome].matrix_local.to_quaternion()
    giro = Euler([math.radians(a) for a in rot], "XYZ").to_quaternion()
    pb.rotation_quaternion = q.inverted() @ giro @ q
    pb.location = q.inverted() @ Vector(loc)
    pb.scale = escala


def chave_pose(quadro, poses):
    for pb in esq.pose.bones:
        posar(pb.name, **poses.get(pb.name, {}))
        for prop in ("rotation_quaternion", "location", "scale"):
            pb.keyframe_insert(prop, frame=quadro, group=pb.name)


def acao_grasnos(nome, quadros):
    """Pato parado que grasna (estica o pescoço e abre as asas) nos quadros dados."""
    acao = bpy.data.actions.new(nome)
    esq.animation_data.action = acao
    asas = lambda g: {"asa.L": dict(rot=(0, -g, 0)), "asa.R": dict(rot=(0, g, 0))}
    chave_pose(0, {})
    for q in quadros:
        chave_pose(q, {})
        chave_pose(q + 3, {"corpo": dict(escala=(1.07, 0.9, 1.07)), "cabeca": dict(rot=(12, 0, 0)), **asas(10)})
        chave_pose(q + 6, {"corpo": dict(escala=(0.95, 1.1, 0.95)), "cabeca": dict(rot=(-22, 0, 0)), **asas(40)})
        chave_pose(q + 14, {})
    return acao


def usar_animacao(nome_ou_acao):
    esq.animation_data.action = (bpy.data.actions[nome_ou_acao]
                                 if isinstance(nome_ou_acao, str) else nome_ou_acao)


# ---------------------------------------------------------------- patinho (modelo simples)
col_patinho = bpy.data.collections.new("Patinho")
scene.collection.children.link(col_patinho)
amarelo, laranja_pato = fosco("FFD43B"), bpy.data.materials["BicoPes"]
olho_pato = bpy.data.materials["Olho"]
malha("PatinhoCorpo", bm_esfera((0.30, 0.36, 0.27)), amarelo, col_patinho, loc=(0, 0.05, 0.32), suave=True, subdiv=1)
malha("PatinhoCabeca", bm_esfera((0.21, 0.21, 0.2)), amarelo, col_patinho, loc=(0, -0.16, 0.68), suave=True, subdiv=1)
malha("PatinhoBico", bm_esfera((0.10, 0.09, 0.035)), laranja_pato, col_patinho, loc=(0, -0.38, 0.64), suave=True)
for lado in (-1, 1):
    malha("PatinhoOlho", bm_esfera((0.04, 0.04, 0.045), 8, 6), olho_pato, col_patinho,
          loc=(lado * 0.1, -0.33, 0.75), suave=True)
    malha("PatinhoPe", bm_caixa((0.12, 0.18, 0.04)), laranja_pato, col_patinho, loc=(lado * 0.1, -0.08, 0.02))
bpy.context.view_layer.layer_collection.children["Patinho"].exclude = True

# ---------------------------------------------------------------- cena, câmera e ambiente
cena_col = bpy.data.collections.new("Cena")
scene.collection.children.link(cena_col)

cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
cam.data.lens = 35
cam.data.clip_end = 300
scene.collection.objects.link(cam)
mira = bpy.data.objects.new("Mira", None)
scene.collection.objects.link(mira)
restricao = cam.constraints.new("TRACK_TO")
restricao.target = mira
restricao.track_axis = "TRACK_NEGATIVE_Z"
restricao.up_axis = "UP_Y"
scene.camera = cam

# Textos ficam presos na câmera a 5 unidades: plano de 2.89 x 5.14 (largura x altura).
DIST_TEXTO = 5.0
MEIA_ALTURA = DIST_TEXTO * 18 / 35
MEIA_LARGURA = MEIA_ALTURA * 1080 / 1920


def novo(nome, dados=None):
    o = bpy.data.objects.new(nome, dados)
    cena_col.objects.link(o)
    return o


def limpar():
    for o in list(cena_col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    esq.animation_data.action = None
    for pb in esq.pose.bones:
        posar(pb.name)
    cam.animation_data_clear()
    mira.animation_data_clear()
    ambiente()


def ambiente(luz=1.0, cor=ESCURO, forca=1.0):
    mundo.node_tree.animation_data_clear()
    fundo.inputs["Color"].default_value = linear(cor)
    fundo.inputs["Strength"].default_value = forca
    for luz_obj, energia in LUZES:
        luz_obj.data.animation_data_clear()
        luz_obj.data.energy = energia * luz


def camera(de, mira_de, para=None, mira_para=None, ultimo=None):
    cam.location = de
    cam.keyframe_insert("location", frame=0)
    mira.location = mira_de
    mira.keyframe_insert("location", frame=0)
    if para:
        cam.location = para
        cam.keyframe_insert("location", frame=ultimo)
    if mira_para:
        mira.location = mira_para
        mira.keyframe_insert("location", frame=ultimo)


def surgir(o, entra, sai=None, dur=6):
    """Entra com 'pulinho' (easing BACK) e some encolhendo."""
    o.scale = (0, 0, 0)
    o.keyframe_insert("scale", frame=entra)
    o.scale = (1, 1, 1)
    o.keyframe_insert("scale", frame=entra + dur)
    if sai:
        o.keyframe_insert("scale", frame=sai - 4)
        o.scale = (0, 0, 0)
        o.keyframe_insert("scale", frame=sai)
    for fc in curvas(o.animation_data.action):
        for k in fc.keyframe_points:
            if abs(k.co.x - entra) < 0.5:
                k.interpolation = "BACK"
                k.easing = "EASE_OUT"


def texto(corpo, y, tam=0.24, cor=BRANCO, entra=0, sai=None, fonte=None, x=-0.08):
    # x levemente à esquerda: os botões do TikTok ficam no lado direito
    d = bpy.data.curves.new("Texto", "FONT")
    d.body = corpo
    d.font = fonte or NORMAL
    d.size = tam
    d.align_x, d.align_y = "CENTER", "CENTER"
    d.materials.append(emissivo(cor))
    o = novo("Texto", d)
    o.parent = cam
    o.location = (x, y, -DIST_TEXTO)
    surgir(o, entra, sai)
    return o


def na_tela(ponto, quadro):
    """Posição de um ponto do mundo no plano dos textos, no quadro dado."""
    scene.frame_set(quadro)
    u = world_to_camera_view(scene, cam, Vector(ponto))
    return (u.x - 0.5) * 2 * MEIA_LARGURA, (u.y - 0.5) * 2 * MEIA_ALTURA


def quack(ponto, quadro, tam=0.26):
    x, y = na_tela(ponto, quadro)
    x = max(-1.1, min(0.95, x))
    texto("QUACK!", y, tam, LARANJA, quadro, quadro + 20, TITULO, x)


def onda(centro, quadro, alcance=8.0, dur=36, cor=CIANO, forca=4.0, na_camera=False):
    """Anel de sonar que cresce e apaga."""
    mat = emissivo(cor, forca, unico=True)
    bm = bm_anel(0.012 if na_camera else 0.02)
    me = bpy.data.meshes.new("Onda")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    o = novo("Onda", me)
    if na_camera:
        o.parent = cam
        o.location = (centro[0], centro[1], -DIST_TEXTO - 0.5)
    else:
        o.location = (centro[0], centro[1], 0.03)
    o.scale = (0.01, 0.01, 1)
    o.keyframe_insert("scale", frame=quadro)
    o.scale = (alcance, alcance, 1)
    o.keyframe_insert("scale", frame=quadro + dur)
    # some ficando transparente (só apagar a emissão deixaria um anel preto)
    nt = mat.node_tree
    vazio = nt.nodes.new("ShaderNodeBsdfTransparent")
    mistura = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(vazio.outputs[0], mistura.inputs[1])
    nt.links.new(nt.nodes["Emission"].outputs[0], mistura.inputs[2])
    nt.links.new(mistura.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    opaco = mistura.inputs["Fac"]
    for q, v in ((0, 0.0), (quadro - 1, 0.0), (quadro, 1.0), (quadro + dur, 0.0)):
        opaco.default_value = v
        opaco.keyframe_insert("default_value", frame=max(0, q))
    # fora da janela da onda ela nem existe
    for q, escondido in ((0, True), (quadro, False), (quadro + dur, True)):
        o.hide_render = escondido
        o.keyframe_insert("hide_render", frame=q)
    return o


def faixa_escura(y_baixo=0.75):
    """Véu escuro no topo da tela para o texto não brigar com o neon."""
    m = bpy.data.materials.new("Veu")
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    rampa = nt.nodes.new("ShaderNodeMapRange")
    rampa.inputs["From Max"].default_value = 0.45
    rampa.inputs["To Max"].default_value = 1.0   # topo opaco: sem granulado de transparência
    vazio = nt.nodes.new("ShaderNodeBsdfTransparent")
    escuro = nt.nodes.new("ShaderNodeEmission")
    escuro.inputs["Color"].default_value = linear("0B0910")
    mistura = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Y"], rampa.inputs["Value"])
    nt.links.new(rampa.outputs["Result"], mistura.inputs["Fac"])
    nt.links.new(vazio.outputs[0], mistura.inputs[1])
    nt.links.new(escuro.outputs[0], mistura.inputs[2])
    nt.links.new(mistura.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    altura = MEIA_ALTURA - y_baixo + 0.1
    me = bpy.data.meshes.new("Veu")
    bm = bm_retangulo(2 * MEIA_LARGURA + 0.2, altura)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    o = novo("Veu", me)
    o.parent = cam
    o.location = (0, y_baixo + altura / 2, -DIST_TEXTO - 0.05)


def chao(cor="1A1528"):
    bm = bm_retangulo(80, 80)
    me = bpy.data.meshes.new("Chao")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(fosco(cor, 0.95))
    o = novo("Chao", me)
    return o


def pato(loc=(0, 0, 0), rot=0, escala=1.0, tinta=(1, 1, 1)):
    e = novo("Pato")
    e.instance_type = "COLLECTION"
    e.instance_collection = col_pato
    e.location = loc
    e.rotation_euler = (0, 0, math.radians(rot))
    e.scale = (escala,) * 3
    e["tinta"] = list(tinta)
    return e


def patinho(loc, rot=0):
    e = novo("Patinho")
    e.instance_type = "COLLECTION"
    e.instance_collection = col_patinho
    e.location = loc
    e.rotation_euler = (0, 0, math.radians(rot))
    return e


# ---------------------------------------------------------------- sala gigante em neon (sonar)
def sala_gigante(origem=(0, 0, 0)):
    """Móveis enormes (escala de pato) que só aparecem quando a onda do sonar passa."""
    m = bpy.data.materials.new("Sonar")
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    novo_no = lambda tipo, **kw: (lambda n: ([setattr(n, k, v) for k, v in kw.items()], n)[1])(nt.nodes.new(tipo))
    geo = novo_no("ShaderNodeNewGeometry")
    dist = novo_no("ShaderNodeVectorMath", operation="DISTANCE")
    dist.inputs[1].default_value = origem
    raio = novo_no("ShaderNodeValue")
    brilho = novo_no("ShaderNodeValue")
    menos = novo_no("ShaderNodeMath", operation="SUBTRACT")
    absoluto = novo_no("ShaderNodeMath", operation="ABSOLUTE")
    banda = novo_no("ShaderNodeMapRange", clamp=True)
    banda.inputs["From Max"].default_value = 1.2
    banda.inputs["To Min"].default_value = 6.0
    banda.inputs["To Max"].default_value = 0.0
    dentro = novo_no("ShaderNodeMath", operation="LESS_THAN")
    resto = novo_no("ShaderNodeMath", operation="MULTIPLY")
    resto_forte = novo_no("ShaderNodeMath", operation="MULTIPLY")
    resto_forte.inputs[1].default_value = 2.5
    soma = novo_no("ShaderNodeMath", operation="ADD")
    em = novo_no("ShaderNodeEmission")
    em.inputs["Color"].default_value = linear(CIANO)
    lig = nt.links.new
    lig(geo.outputs["Position"], dist.inputs[0])
    lig(dist.outputs["Value"], menos.inputs[0])
    lig(raio.outputs[0], menos.inputs[1])
    lig(menos.outputs[0], absoluto.inputs[0])
    lig(absoluto.outputs[0], banda.inputs["Value"])
    lig(dist.outputs["Value"], dentro.inputs[0])
    lig(raio.outputs[0], dentro.inputs[1])
    lig(dentro.outputs[0], resto.inputs[0])
    lig(brilho.outputs[0], resto.inputs[1])
    lig(resto.outputs[0], resto_forte.inputs[0])
    lig(banda.outputs["Result"], soma.inputs[0])
    lig(resto_forte.outputs[0], soma.inputs[1])
    lig(soma.outputs[0], em.inputs["Strength"])
    lig(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])

    def caixa(centro, dims):
        o = malha("Movel", bm_caixa(dims), m, cena_col, loc=centro)
        fio = o.modifiers.new("Fio", "WIREFRAME")
        fio.thickness = 0.07
        fio.use_even_offset = True

    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=16, y_segments=16, size=24)
    piso = malha("Piso", bm, m, cena_col, loc=(0, 6, 0.01))
    fio = piso.modifiers.new("Fio", "WIREFRAME")
    fio.thickness = 0.05

    caixa((-6, 9, 1.0), (9, 4, 2.0))            # sofá: assento
    caixa((-6, 10.8, 3.4), (9, 0.8, 4.8))       # encosto
    caixa((-10.4, 9, 2.4), (0.9, 4, 2.8))       # braços
    caixa((-1.6, 9, 2.4), (0.9, 4, 2.8))
    caixa((-8.1, 8.8, 2.3), (3.9, 3.3, 0.6))    # almofadas
    caixa((-3.9, 8.8, 2.3), (3.9, 3.3, 0.6))
    caixa((6.5, 5, 3.2), (6.5, 4, 0.3))         # mesa
    for dx in (-2.9, 2.9):
        for dy in (-1.7, 1.7):
            caixa((6.5 + dx, 5 + dy, 1.5), (0.35, 0.35, 3.0))
    caixa((1.0, 15, 4.4), (0.5, 0.5, 8.8))      # porta
    caixa((5.4, 15, 4.4), (0.5, 0.5, 8.8))
    caixa((3.2, 15, 9.0), (4.9, 0.5, 0.5))
    caixa((12, 12, 6.5), (4, 1.6, 13))          # estante
    for z in (3.2, 6.5, 9.8):
        caixa((12, 11.6, z), (3.8, 1.2, 0.15))
    caixa((-13, 3, 4.5), (0.25, 0.25, 9.0))     # abajur
    caixa((-13, 3, 9.4), (2.2, 2.2, 1.4))
    return raio, brilho


def pulsos(raio, brilho, quadros, alcance=34.0, dur=44):
    """Anima o sonar da sala: cada quack manda uma onda que acende e deixa um rastro fraco."""
    chaves_r, chaves_b = [(0, 0.0)], [(0, 0.0)]
    for i, q in enumerate(quadros):
        proximo = quadros[i + 1] if i + 1 < len(quadros) else 10 ** 6
        chaves_r += [(q - 1, chaves_r[-1][1]), (q, 0.0), (q + dur, alcance)]
        chaves_b += [(q - 1, chaves_b[-1][1]), (q, 1.0), (q + dur, 0.3)]
        if q + dur + 40 < proximo - 1:
            chaves_b.append((q + dur + 40, 0.06))
    for no, chaves in ((raio, chaves_r), (brilho, chaves_b)):
        for q, v in chaves:
            no.outputs[0].default_value = v
            no.outputs[0].keyframe_insert("default_value", frame=max(0, q))
    for m in bpy.data.materials:
        if m.name.startswith("Sonar"):
            interpolacao(m.node_tree, "LINEAR")


# ---------------------------------------------------------------- o dono sonâmbulo
def gigante():
    raiz = novo("Gigante")
    pele, pijama = fosco("D9A98F"), fosco("34426E")
    gorro, branco, chinelo = fosco("3F4F8F"), fosco("EDEDED"), fosco("C98BB0")

    def peca(nome, bm, mat, loc, rot=(0, 0, 0), pai=raiz, subdiv=1):
        o = malha(nome, bm, mat, cena_col, loc=loc, rot=rot, suave=True, subdiv=subdiv)
        o.parent = pai
        return o

    peca("Tronco", bm_esfera((1.15, 0.75, 1.6)), pijama, (0, 0, 5.0))
    peca("Cabeca", bm_esfera((0.68, 0.7, 0.76)), pele, (0, -0.1, 7.05))
    peca("Gorro", bm_cilindro(0.66, 1.5, 12, 0.05), gorro, (0.1, 0.25, 7.95), rot=(-28, 12, 0), subdiv=0)
    peca("Pompom", bm_esfera((0.2, 0.2, 0.2)), branco, (0.35, 0.95, 8.45))
    for lado in (-1, 1):
        peca("Olho", bm_caixa((0.22, 0.04, 0.05)), fosco("2A1A14"), (lado * 0.26, -0.78, 7.1), subdiv=0)
        peca("Braco", bm_cilindro(0.3, 2.8, 12), pijama, (lado * 1.05, -1.45, 5.95), rot=(90, 0, 0))
        peca("Mao", bm_esfera((0.3, 0.32, 0.26)), pele, (lado * 1.05, -2.95, 5.95))
        quadril = novo("Quadril")
        quadril.parent = raiz
        quadril.location = (lado * 0.55, 0, 3.7)
        peca("Perna", bm_cilindro(0.42, 3.4, 12), pijama, (0, 0, -1.7), pai=quadril)
        peca("Chinelo", bm_esfera((0.42, 0.75, 0.22)), chinelo, (0, -0.3, -3.55), pai=quadril)
    return raiz


# ---------------------------------------------------------------- as cenas
CENAS = []


def cena(nome, quadros):
    def registrar(funcao):
        CENAS.append((nome, quadros, funcao))
        return funcao
    return registrar


@cena("gancho", 84)
def _(n):
    camera((0, -10, 1), (0, 0, 1))
    texto("QUACK!", 0.35, 0.66, LARANJA, 3, 32, TITULO, x=0)
    onda((0, 0.35), 5, alcance=3.2, dur=34, na_camera=True)
    onda((0, 0.35), 14, alcance=3.2, dur=34, na_camera=True, forca=2.0)
    texto("e se fazer\nbarulho fosse\no único jeito\nde enxergar?", 0.35, 0.3, BRANCO, 36, x=0)


@cena("titulo", 108)
def _(n):
    chao()
    usar_animacao("parado")
    pato()
    camera((0, -6.0, 1.6), (0, 0, 1.75), para=(0, -5.2, 1.5), ultimo=n - 1)
    for q in (4, 40, 76):
        onda((0, 0), q, alcance=7, dur=40, forca=3.0)
    texto("QUACKROOM", 1.85, 0.48, LARANJA, 4, fonte=TITULO)
    texto("terror cooperativo", 1.38, 0.24, BRANCO, 16)
    texto("1 a 4 jogadores · online", 1.08, 0.18, CIANO, 26)


@cena("historia", 144)
def _(n):
    ambiente(luz=0.3, cor="0B0910")
    faixa_escura(0.7)
    raio, brilho = sala_gigante()
    pulsos(raio, brilho, [18, 84])
    usar_animacao(acao_grasnos("grasno_historia", [14, 80]))
    pato()
    camera((0, -6.5, 0.9), (0, 4, 3.2), para=(0, -9.5, 1.6), mira_para=(0, 4, 3.8), ultimo=n - 1)
    texto("uma ninhada\nde patinhos se\nperdeu dentro\nde uma casa...", 1.65, 0.26, BRANCO, 4, 70)
    texto("pra um pato,\ncada cômodo é", 1.95, 0.26, BRANCO, 74)
    texto("GIGANTE.", 1.3, 0.52, LARANJA, 86, fonte=TITULO)


@cena("sonar", 168)
def _(n):
    ambiente(luz=0.15, cor="0B0910")
    faixa_escura(0.75)
    raio, brilho = sala_gigante()
    pulsos(raio, brilho, [54, 102])
    usar_animacao(acao_grasnos("grasno_sonar", [50, 98]))
    pato()
    camera((6.5, -9.5, 6.0), (0, 3, 1.5), para=(5.0, -8.0, 4.6), ultimo=n - 1)
    texto("a casa tá no\nescuro total.", 1.8, 0.3, BRANCO, 4, 46)
    quack((0, -0.4, 2.2), 52)
    texto("o QUACK é o\nseu sonar.", 1.8, 0.3, BRANCO, 62, 112)
    quack((0, -0.4, 2.2), 100)
    texto("mas todo barulho\nque você faz...", 1.95, 0.25, BRANCO, 116)
    texto("acorda o dono\nda casa.", 1.25, 0.32, LARANJA, 132, fonte=TITULO)


@cena("sonambulo", 168)
def _(n):
    ambiente(luz=0.6)
    chao()
    g = gigante()
    for q, y in ((0, 7.0), (100, 3.2)):
        g.location = (0, y, 0)
        g.keyframe_insert("location", frame=q)
    quadris = [o for o in cena_col.objects if o.name.startswith("Quadril")]
    for i, quadril in enumerate(quadris):
        for q in range(0, 101, 25):
            lado = 1 if (q // 25 + i) % 2 == 0 else -1
            quadril.rotation_euler = (math.radians(12 * lado), 0, 0)
            quadril.keyframe_insert("rotation_euler", frame=q)
    usar_animacao(acao_grasnos("grasno_sonambulo", [30, 62, 94]))
    pato(loc=(0.4, -3.5, 0), rot=-15)
    camera((0, -14, 2.4), (0, 0, 4.4), para=(0, -12.5, 2.0), ultimo=n - 1)

    # barra de sono no topo (some depois que ele acorda)
    fundo_barra = novo("BarraFundo", bpy.data.meshes.new("BarraFundo"))
    bm = bm_retangulo(2.3, 0.14)
    bm.to_mesh(fundo_barra.data)
    bm.free()
    fundo_barra.data.materials.append(emissivo("3A3550"))
    fundo_barra.parent = cam
    fundo_barra.location = (-0.08, 2.0, -DIST_TEXTO - 0.01)
    barra = novo("Barra", bpy.data.meshes.new("Barra"))
    bm = bm_retangulo(1.0, 0.14, ancora_esquerda=True)
    bm.to_mesh(barra.data)
    bm.free()
    mat_barra = emissivo("8FD16A", unico=True)
    barra.data.materials.append(mat_barra)
    barra.parent = cam
    barra.location = (-1.23, 2.0, -DIST_TEXTO)
    cor_barra = mat_barra.node_tree.nodes["Emission"].inputs["Color"]
    etapas = [(0, 0.12, "8FD16A", "sono: profundo"), (34, 0.42, "FFD43B", "sono: inquieto"),
              (66, 0.72, LARANJA, "sono: quase acordado"), (98, 1.0, VERMELHO, "ACORDOU!")]
    for i, (q, valor, cor, rotulo) in enumerate(etapas):
        for quadro, v in ((q - 1, etapas[i - 1][1] if i else valor), (q + 4, valor)):
            barra.scale = (2.3 * v, 1, 1)
            barra.keyframe_insert("scale", frame=max(0, quadro))
        cor_barra.default_value = linear(cor)
        cor_barra.keyframe_insert("default_value", frame=q)
        texto(rotulo, 2.25, 0.16, VERMELHO if i == 3 else BRANCO, q,
              etapas[i + 1][0] if i < 3 else 108, TITULO if i == 3 else NORMAL)
    interpolacao(mat_barra.node_tree, "CONSTANT")
    for o in (fundo_barra, barra):
        for q, escondido in ((0, False), (106, True)):
            o.hide_render = escondido
            o.keyframe_insert("hide_render", frame=q)

    texto("o dono da casa\né sonâmbulo.", 1.5, 0.28, BRANCO, 4, 30)
    for q in (30, 62, 94):
        quack((0.4, -3.5, 2.3), q, 0.26)
    for i, q in enumerate((8, 40, 72)):
        z = texto("Z" if i < 2 else "Zz", 0.0, 0.24 + 0.06 * i, CINZA, q, q + 26, TITULO)
        x0, y0 = na_tela((0.6, 3.5, 8.2), q)
        z.location = (x0 + 0.3, y0, -DIST_TEXTO)
        z.keyframe_insert("location", frame=q)
        z.location = (x0 + 0.55, y0 + 0.5, -DIST_TEXTO)
        z.keyframe_insert("location", frame=q + 26)

    # flash: ele acordou e acendeu a luz
    entrada_cor, entrada_forca = fundo.inputs["Color"], fundo.inputs["Strength"]
    for q, cor, forca in ((100, ESCURO, 1.0), (104, "FFF4DC", 3.0)):
        entrada_cor.default_value = linear(cor)
        entrada_forca.default_value = forca
        entrada_cor.keyframe_insert("default_value", frame=q)
        entrada_forca.keyframe_insert("default_value", frame=q)
    for luz_obj, energia in LUZES:
        for q, fator in ((100, 0.6), (104, 2.2)):
            luz_obj.data.energy = energia * fator
            luz_obj.data.keyframe_insert("energy", frame=q)
    texto("se ele acordar,\na luz acende...", 2.0, 0.28, ESCURO, 110)
    texto("e aí já era.", 1.42, 0.4, "C81E1E", 128, fonte=TITULO)


@cena("patinhos", 144)
def _(n):
    chao()
    usar_animacao("andar_frente")
    p = pato(rot=90)
    filhotes = [patinho((0, 0, 0), 90) for _ in range(4)]
    for q in (0, n - 1):
        x = -2.6 + 4.6 * q / (n - 1)
        p.location = (x, 0, 0)
        p.keyframe_insert("location", frame=q)
    interpolacao(p, "LINEAR")
    for i, f in enumerate(filhotes):
        for q in range(0, n, 2):
            x = -2.6 + 4.6 * q / (n - 1) - 1.25 - 0.95 * i
            f.location = (x, 0, 0.16 * abs(math.sin(math.pi * q / 8 + i)))
            f.keyframe_insert("location", frame=q)
    camera((0, -10, 1.9), (0, 0, 1.7))
    onda((-2.6, 0), 6, alcance=5, dur=34)
    quack((-2.4, 0, 2.4), 6, 0.26)
    texto("os patinhos seguem\no último QUACK\nque ouvirem.", 1.8, 0.26, BRANCO, 14, 82)
    texto("leve todos de\nvolta pro ninho!", 1.8, 0.28, LARANJA, 86, fonte=TITULO)


@cena("coop", 120)
def _(n):
    chao()
    usar_animacao("parado")
    tintas = [(1, 1, 1), (0.62, 0.45, 0.32), (0.6, 0.64, 0.7), (1.0, 0.85, 0.4)]
    for x, tinta in zip((-2.1, -0.75, 0.6, 1.95), tintas):
        pato(loc=(x, 0, 0), tinta=tinta)
    camera((-0.1, -10.5, 2.3), (-0.1, 0, 2.0))
    texto("jogue com até\n4 amigos online", 1.8, 0.3, BRANCO, 4, 58)
    onda((-0.75, 0), 64, alcance=7, dur=40)
    quack((-0.75, 0, 2.6), 62, 0.26)
    texto("alguém tem que\ngrasnar...", 1.9, 0.3, BRANCO, 62)
    texto("e virar\na isca.", 1.1, 0.4, LARANJA, 84, fonte=TITULO)


@cena("recrutamento", 168)
def _(n):
    chao()
    usar_animacao("parado")
    pato()
    camera((0, -7.5, 2.4), (0, 0, 2.5))
    for q in (0, 56, 112):
        onda((0, 0), q, alcance=6, dur=44, forca=2.5)
    texto("tô criando o", 2.12, 0.22, BRANCO, 4)
    texto("QUACKROOM", 1.76, 0.44, LARANJA, 8, fonte=TITULO)
    texto("e procuro gente\npra entrar no time!", 1.3, 0.23, BRANCO, 20, 120)
    for i, papel in enumerate(("• arte 3D e modelagem", "• som e música",
                               "• programação (Godot)", "• level design")):
        texto(papel, 0.86 - 0.25 * i, 0.2, CIANO, 44 + 9 * i, 120)
    texto("comenta QUACK\nque eu te chamo!", 0.85, 0.3, LARANJA, 124, fonte=TITULO)


@cena("final", 84)
def _(n):
    chao()
    usar_animacao("pular")
    p = pato()
    for q, z in ((0, 0), (6, 0), (12, 0.7), (18, 0.25), (21, 0)):
        p.location = (0, 0, z)
        p.keyframe_insert("location", frame=q)
    camera((0, -7.5, 2.4), (0, 0, 2.5))
    onda((0, 0), 22, alcance=7, dur=40)
    texto("QUACKROOM", 1.6, 0.5, LARANJA, 6, fonte=TITULO)
    texto("faça barulho.", 1.02, 0.3, BRANCO, 20)
    texto("se tiver coragem.", 0.62, 0.28, CIANO, 32)
    texto("em desenvolvimento · Godot 4", 0.22, 0.14, CINZA, 44)


# ---------------------------------------------------------------- render
pasta_quadros = os.path.join(SAIDA, "amostra" if MODO.startswith("amostra") else "quadros")
FILTRO = MODO.split(":")[1] if ":" in MODO else None   # amostra:<cena>[:<quadro>]
MODO = MODO.split(":")[0]
QUADRO_UNICO = int(argv[1].split(":")[2]) if argv[1:] and argv[1].count(":") == 2 else None
for i, (nome, n, montar) in enumerate(CENAS):
    if (MODO not in ("completo", "amostra") and MODO != nome) or (FILTRO and FILTRO != nome):
        continue
    limpar()
    montar(n)
    scene.frame_start, scene.frame_end = 0, n - 1
    if MODO == "amostra":
        for q in ([QUADRO_UNICO] if QUADRO_UNICO is not None else [int(n * f) for f in (0.25, 0.55, 0.9)]):
            scene.frame_set(q)
            scene.render.filepath = os.path.join(pasta_quadros, f"{i:02d}_{nome}_{q:03d}.png")
            bpy.ops.render.render(write_still=True)
    else:
        scene.render.filepath = os.path.join(pasta_quadros, f"{i:02d}_{nome}", "f_")
        bpy.ops.render.render(animation=True)
    print("CENA_OK", nome, flush=True)

if MODO == "completo":
    lista = os.path.join(pasta_quadros, "lista.txt")
    with open(lista, "w") as arq:
        for i, (nome, n, _) in enumerate(CENAS):
            clipe = os.path.join(pasta_quadros, f"{i:02d}_{nome}.mp4")
            dur = n / FPS
            fades = f"fade=t=in:st=0:d=0.12,fade=t=out:st={dur - 0.12:.3f}:d=0.12" if i else \
                f"fade=t=out:st={dur - 0.12:.3f}:d=0.12"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-start_number", "0",
                            "-i", os.path.join(pasta_quadros, f"{i:02d}_{nome}", "f_%04d.png"),
                            "-vf", fades, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", clipe],
                           check=True)
            arq.write(f"file '{clipe}'\n")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista,
                    "-c", "copy", "-movflags", "+faststart", os.path.join(SAIDA, "quackroom_tiktok.mp4")],
                   check=True)
    print("VIDEO_OK", os.path.join(SAIDA, "quackroom_tiktok.mp4"))
