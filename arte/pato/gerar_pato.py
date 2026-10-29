"""Gera o pato do Quackroom (fantasia de Halloween) em low-poly no Blender.

Uso (sem abrir o Blender):
    blender --background --factory-startup --python arte/pato/gerar_pato.py -- arte/pato

Saídas na pasta indicada:
    pato.blend                      modelo + cena da folha de ângulos
    renders/pato_turnaround.png     frente, 3/4, perfil e costas
    renders/pato_closeup.png        rosto de perto (para conferir detalhes)
"""
import bpy
import bmesh
import math
import os
import sys
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else os.getcwd())
os.makedirs(os.path.join(OUT, "renders"), exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# Superfície de uma metaball sozinha = 0.575 * raio (stiffness 2, threshold 0.6).
METABALL_K = 0.575
FRENTE = Vector((0, -1, 0))  # o pato olha para -Y (vista frontal do Blender)


# ---------------------------------------------------------------- materiais
def linear(hexcor):
    h = hexcor.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda x: x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]), 1.0)


def material(nome, hexcor, rugosidade=0.85):
    m = bpy.data.materials.new(nome)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = linear(hexcor)
    bsdf.inputs["Roughness"].default_value = rugosidade
    m.diffuse_color = linear(hexcor)
    return m


def material_cor_vertice(nome, atributo, rugosidade=0.85):
    """Cor vem dos vértices (degradê suave, sem borda serrilhada)."""
    m = material(nome, "FFFFFF", rugosidade)
    nos = m.node_tree.nodes
    cor = nos.new("ShaderNodeVertexColor")
    cor.layer_name = atributo
    m.node_tree.links.new(cor.outputs["Color"], nos["Principled BSDF"].inputs["Base Color"])
    return m


COR_PENAS, COR_BARRIGA = "F3ECDF", "F5C4A0"
M = {
    "penas": material("Penas", COR_PENAS),
    "penas_corpo": material_cor_vertice("PenasCorpo", "Cor"),
    "laranja": material("BicoPes", "FF8A1E", 0.6),
    "olho": material("Olho", "2E1B10", 0.25),
    "brilho": material("BrilhoOlho", "FFFFFF", 0.2),
    "chapeu": material("Chapeu", "1F1F24", 0.95),
    "costura": material("Costura", "8E8E8E"),
    "cach_laranja": material("CachecolLaranja", "D8611A", 0.95),
    "cach_preto": material("CachecolPreto", "1B1B1B", 0.95),
    "abobora": material("Abobora", "EF7516", 0.7),
    "abobora_rosto": material("AboboraRosto", "3A1606", 0.9),
    "alca": material("Alca", "2B2B2B", 0.5),
}

colecao = bpy.data.collections.new("Pato")
scene.collection.children.link(colecao)


# ---------------------------------------------------------------- utilitários
def criar_objeto(nome, bm, materiais, loc=(0, 0, 0), rot=(0, 0, 0), escala=(1, 1, 1)):
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    for m in materiais if isinstance(materiais, list) else [materiais]:
        me.materials.append(m)
    o = bpy.data.objects.new(nome, me)
    colecao.objects.link(o)
    o.location = loc
    o.rotation_euler = Euler([math.radians(a) for a in rot])
    o.scale = escala
    return o


def esfera_bm(segmentos=10, aneis=7):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segmentos, v_segments=aneis, radius=1.0)
    return bm


def aplicar_modificadores(o):
    dg = bpy.context.evaluated_depsgraph_get()
    novo = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    antigo = o.data
    o.modifiers.clear()
    o.data = novo
    bpy.data.meshes.remove(antigo)


def pontos_mundo(o):
    mw = o.matrix_world
    return [mw @ v.co for v in o.data.vertices]


# ---------------------------------------------------------------- corpo (metaballs)
mb = bpy.data.metaballs.new("CorpoMB")
mb.resolution = 0.025
mb.threshold = 0.6
mb_obj = bpy.data.objects.new("CorpoMB", mb)
scene.collection.objects.link(mb_obj)


def bola(centro, raios, rot=(0, 0, 0)):
    e = mb.elements.new()
    e.type = "ELLIPSOID"
    r = max(raios)
    e.co = centro
    e.radius = r / METABALL_K
    e.stiffness = 2.0
    e.size_x, e.size_y, e.size_z = (x / r for x in raios)
    e.rotation = Euler([math.radians(a) for a in rot]).to_quaternion()


bola((0, 0.05, 0.77), (0.45, 0.42, 0.48))      # tronco
bola((0, -0.04, 0.59), (0.39, 0.37, 0.33))     # barriga baixa (forma de pera)
bola((0, -0.08, 1.30), (0.21, 0.21, 0.28))     # pescoço
bola((0, -0.10, 1.71), (0.33, 0.32, 0.30))     # cabeça

dg = bpy.context.evaluated_depsgraph_get()
me_corpo = bpy.data.meshes.new_from_object(mb_obj.evaluated_get(dg))
bpy.data.objects.remove(mb_obj)
bpy.data.metaballs.remove(mb)
corpo = bpy.data.objects.new("Corpo", me_corpo)
colecao.objects.link(corpo)

# Decimate = o visual low-poly facetado da referência.
tris = sum(len(p.vertices) - 2 for p in me_corpo.polygons)
dec = corpo.modifiers.new("Decimate", "DECIMATE")
dec.ratio = 650 / tris
dec.use_symmetry = True
dec.symmetry_axis = "X"
aplicar_modificadores(corpo)

corpo.data.materials.append(M["penas_corpo"])
# barriga pêssego esfumada: elipse na frente que some aos poucos nas bordas
penas, barriga = Vector(linear(COR_PENAS)[:3]), Vector(linear(COR_BARRIGA)[:3])
atributo_cor = corpo.data.color_attributes.new("Cor", "FLOAT_COLOR", "POINT")
for v in corpo.data.vertices:
    c = v.co
    dist = (c.x / 0.33) ** 2 + ((c.z - 0.62) / 0.32) ** 2
    t = max(0.0, min(1.0, (1.25 - dist) / 0.5)) * max(0.0, min(1.0, -c.y / 0.15))
    atributo_cor.data[v.index].color = (*penas.lerp(barriga, t), 1.0)

bvh = BVHTree.FromPolygons([v.co.copy() for v in corpo.data.vertices],
                           [list(p.vertices) for p in corpo.data.polygons])


def superficie(alvo, direcao):
    """Ponto da pele do pato na direção `direcao`, vindo de fora até `alvo`."""
    d = Vector(direcao).normalized()
    loc, normal, _, _ = bvh.ray_cast(Vector(alvo) + d * 3.0, -d)
    return loc, normal


CABECA = Vector((0, -0.10, 1.70))

# ---------------------------------------------------------------- olhos
for lado in (-1, 1):
    loc, n = superficie(CABECA, (lado * 0.6, -1.0, 0.25))
    bm = esfera_bm(8, 6)
    criar_objeto(f"Olho.{'E' if lado < 0 else 'D'}", bm, M["olho"],
                 loc=loc - n * 0.025, escala=(0.078, 0.078, 0.085))
    bm = esfera_bm(6, 4)
    brilho = loc + n * 0.04 + Vector((lado * 0.012, 0, 0.03))
    criar_objeto(f"BrilhoOlho.{'E' if lado < 0 else 'D'}", bm, M["brilho"],
                 loc=brilho, escala=(0.02, 0.02, 0.02))

# ---------------------------------------------------------------- bico
loc_bico, _ = superficie(CABECA, (0, -1, -0.3))


def bico(nome, largura, comprimento, espessura, dz):
    bm = esfera_bm(10, 6)
    for v in bm.verts:
        frente = max(0.0, -v.co.y)               # 0 na base, 1 na ponta
        v.co.x *= 1.0 + 0.35 * frente            # mais largo na ponta (bico de pato)
        v.co.z *= 1.0 - 0.25 * frente
    return criar_objeto(nome, bm, M["laranja"],
                        loc=loc_bico + Vector((0, -comprimento * 0.55, dz)),
                        rot=(4, 0, 0), escala=(largura, comprimento, espessura))


bico("BicoCima", 0.15, 0.17, 0.065, 0.0)
bico("BicoBaixo", 0.12, 0.13, 0.04, -0.05)

# ---------------------------------------------------------------- asas
pontas_asas = {}
for lado in (-1, 1):
    bm = esfera_bm(8, 7)
    for v in bm.verts:
        baixo = max(0.0, -v.co.z)
        v.co.y += 0.45 * baixo * baixo           # ponta da asa puxada para trás
        v.co.x *= 1.0 - 0.3 * baixo
    asa = criar_objeto(f"Asa.{'E' if lado < 0 else 'D'}", bm, M["penas"],
                       loc=(lado * 0.45, 0.06, 0.78), rot=(0, lado * -16, lado * 6),
                       escala=(0.14, 0.26, 0.36))
    bpy.context.view_layer.update()
    pontas_asas[lado] = min(pontos_mundo(asa), key=lambda p: p.z)

# ---------------------------------------------------------------- rabo (tufo virado para cima)
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.15, radius2=0.0, depth=0.32)
bmesh.ops.translate(bm, vec=(0, 0, 0.16), verts=bm.verts)
bmesh.ops.scale(bm, vec=(1.0, 0.45, 1.0), verts=bm.verts)
criar_objeto("PenaRabo", bm, M["penas"], loc=(0, 0.36, 0.55), rot=(-70, 0, 0))  # abaixo da bolsa

# ---------------------------------------------------------------- pernas e pés
for lado in (-1, 1):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.055, radius2=0.05, depth=0.24)
    criar_objeto(f"Perna.{'E' if lado < 0 else 'D'}", bm, M["laranja"], loc=(lado * 0.2, 0.0, 0.12))

    contorno = [(0.0, 0.06), (-0.07, 0.03), (-0.15, -0.22), (-0.06, -0.16), (0.0, -0.29),
                (0.06, -0.16), (0.15, -0.22), (0.07, 0.03)]
    bm = bmesh.new()
    vs = [bm.verts.new((x * 1.2, y * 1.2, 0.0)) for x, y in contorno]
    face = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, vec=(0, 0, 0.055),
                        verts=[g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    criar_objeto(f"Pe.{'E' if lado < 0 else 'D'}", bm, M["laranja"],
                 loc=(lado * 0.21, -0.02, 0.0), rot=(0, 0, lado * 16))

# ---------------------------------------------------------------- chapéu de bruxa (meia dobrada)
topo, _ = superficie(CABECA, (0, 0.15, 1))
base_chapeu = topo + Vector((0, 0, -0.05))

bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=0.38, radius2=0.37, depth=0.03)
criar_objeto("ChapeuAba", bm, M["chapeu"], loc=base_chapeu, rot=(-6, 4, 0))

bm = bmesh.new()
N, SEG = 7, 9
aneis = []
for i in range(N):
    t = i / N
    r = 0.21 * (1 - t) ** 0.8
    off = Vector((-0.05 * t * t, 0.20 * t * t, 0.46 * t - 0.08 * t ** 3))
    aneis.append([bm.verts.new(off + Vector((math.cos(a) * r, math.sin(a) * r, 0)))
                  for a in (2 * math.pi * k / SEG for k in range(SEG))])
ponta = bm.verts.new(Vector((-0.06, 0.27, 0.40)))
for a, b in zip(aneis, aneis[1:]):
    for k in range(SEG):
        bm.faces.new((a[k], a[(k + 1) % SEG], b[(k + 1) % SEG], b[k]))
for k in range(SEG):
    bm.faces.new((aneis[-1][k], aneis[-1][(k + 1) % SEG], ponta))
bm.faces.new(list(reversed(aneis[0])))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
cone = criar_objeto("ChapeuCone", bm, M["chapeu"], loc=base_chapeu + Vector((0, 0, 0.01)), rot=(-6, 4, 0))

# costuras (pontos claros) descendo pela frente do cone
for i, t in enumerate((0.18, 0.38, 0.58)):
    r = 0.21 * (1 - t) ** 0.8 + 0.006
    a = math.radians(235)
    off = Vector((-0.05 * t * t, 0.20 * t * t, 0.46 * t - 0.08 * t ** 3))
    p = off + Vector((math.cos(a) * r, math.sin(a) * r, 0))
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bpy.context.view_layer.update()  # sem isso matrix_world ainda é a identidade
    ponto = cone.matrix_world @ p
    criar_objeto(f"Costura.{i}", bm, M["costura"], loc=ponto,
                 rot=(-6, 4, math.degrees(a) + 90), escala=(0.012, 0.012, 0.05))

# ---------------------------------------------------------------- cachecol listrado
Z_CACHECOL = 1.20
centro_pescoco = Vector((0, -0.08, Z_CACHECOL))
raio_x = (superficie(centro_pescoco, (1, 0, 0))[0] - centro_pescoco).length
raio_y = (superficie(centro_pescoco, (0, -1, 0))[0] - centro_pescoco).length

bm = bmesh.new()
MAIOR, MENOR, R_TUBO = 18, 6, 0.075
grade = []
for i in range(MAIOR):
    u = 2 * math.pi * i / MAIOR
    eixo = Vector((math.cos(u), math.sin(u), 0))
    anel = []
    for j in range(MENOR):
        w = 2 * math.pi * j / MENOR
        base = Vector((math.cos(u) * (raio_x + 0.02), math.sin(u) * (raio_y + 0.02), 0))
        anel.append(bm.verts.new(base + eixo * (math.cos(w) * R_TUBO) + Vector((0, 0, math.sin(w) * R_TUBO))))
    grade.append(anel)
for i in range(MAIOR):
    a, b = grade[i], grade[(i + 1) % MAIOR]
    for j in range(MENOR):
        f = bm.faces.new((a[j], b[j], b[(j + 1) % MENOR], a[(j + 1) % MENOR]))
        f.material_index = 1 if i % 3 == 2 else 0
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
criar_objeto("CachecolVolta", bm, [M["cach_laranja"], M["cach_preto"]],
             loc=centro_pescoco, rot=(12, 0, 0))

# nó do lado direito do pato (esquerda de quem olha de frente)
ang_no = math.radians(235)
pos_no = centro_pescoco + Vector((math.cos(ang_no) * (raio_x + 0.08), math.sin(ang_no) * (raio_y + 0.08), -0.05))
bm = esfera_bm(7, 5)
criar_objeto("CachecolNo", bm, M["cach_laranja"], loc=pos_no, escala=(0.075, 0.06, 0.07))


def ponta_cachecol(nome, x0, x1, z0, z1, largura, segmentos=9):
    """Faixa que desce do nó encostada no peito, com listras alternadas."""
    bm = bmesh.new()
    linhas = []
    for s in range(segmentos + 1):
        t = s / segmentos
        x = x0 + (x1 - x0) * t
        z = z0 + (z1 - z0) * t
        # o peito é curvo: usa o ponto mais à frente da faixa inteira para nada atravessar
        y = min(superficie(Vector((x + largura * k, 0.0, z + dz)), (0, -1, 0))[0].y
                for k in (-0.5, -0.25, 0, 0.25, 0.5) for dz in (-0.04, 0, 0.04)) - 0.035
        linha = []
        for dx in (-largura / 2, largura / 2):
            frente = Vector((x + dx, y, z))
            linha.append(bm.verts.new(frente))
            linha.append(bm.verts.new(frente + Vector((0, 0.025, 0))))
        linhas.append(linha)
    for s in range(segmentos):
        a, b = linhas[s], linhas[s + 1]
        mat = 1 if s % 3 == 2 else 0
        for q in ((a[0], a[2], b[2], b[0]), (a[1], b[1], b[3], a[3]),
                  (a[0], b[0], b[1], a[1]), (a[2], a[3], b[3], b[2])):
            bm.faces.new(q).material_index = mat
    bm.faces.new((linhas[-1][0], linhas[-1][2], linhas[-1][3], linhas[-1][1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    criar_objeto(nome, bm, [M["cach_laranja"], M["cach_preto"]])


ponta_cachecol("CachecolPonta.1", pos_no.x - 0.02, pos_no.x - 0.08, pos_no.z - 0.04, pos_no.z - 0.46, 0.12)
ponta_cachecol("CachecolPonta.2", pos_no.x + 0.06, pos_no.x + 0.10, pos_no.z - 0.04, pos_no.z - 0.34, 0.11)

# ---------------------------------------------------------------- baldes de abóbora
RX, RZ = 0.12, 0.10
for lado in (-1, 1):
    ponta = pontas_asas[lado]
    centro = ponta + Vector((lado * 0.03, -0.02, -0.20))
    bm = esfera_bm(10, 7)
    for v in bm.verts:
        ang = math.atan2(v.co.y, v.co.x)
        gomo = round(ang / (2 * math.pi / 10))
        if gomo % 2:
            v.co.x *= 0.9
            v.co.y *= 0.9
    criar_objeto(f"Abobora.{'E' if lado < 0 else 'D'}", bm, M["abobora"], loc=centro, escala=(RX, RX, RZ))

    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.075, radius2=0.075, depth=0.01)
    criar_objeto(f"AboboraBoca.{'E' if lado < 0 else 'D'}", bm, M["abobora_rosto"],
                 loc=centro + Vector((0, 0, RZ * 0.93)))

    # rosto de jack-o'-lantern projetado na frente da abóbora
    formas = [
        [(-0.055, 0.015), (-0.02, 0.015), (-0.037, 0.045)],                    # olho
        [(0.02, 0.015), (0.055, 0.015), (0.037, 0.045)],                       # olho
        [(-0.06, -0.015), (-0.03, -0.035), (0.0, -0.02), (0.03, -0.035),       # boca
         (0.06, -0.015), (0.03, -0.055), (-0.03, -0.055)],
    ]
    for k, forma in enumerate(formas):
        bm = bmesh.new()
        frente, tras = [], []
        for x, z in forma:
            y = -math.sqrt(max(0.0, 1 - (x / RX) ** 2 - (z / RZ) ** 2)) * RX * 0.97
            frente.append(bm.verts.new((x, y - 0.004, z)))
            tras.append(bm.verts.new((x, y + 0.01, z)))
        bm.faces.new(frente)
        bm.faces.new(list(reversed(tras)))
        n = len(forma)
        for i in range(n):
            bm.faces.new((frente[i], tras[i], tras[(i + 1) % n], frente[(i + 1) % n]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        criar_objeto(f"AboboraRosto.{lado}.{k}", bm, M["abobora_rosto"], loc=centro)

    # alça em arco até a ponta da asa
    curva = bpy.data.curves.new(f"Alca.{lado}", "CURVE")
    curva.dimensions = "3D"
    curva.bevel_depth = 0.008
    curva.bevel_resolution = 1
    spl = curva.splines.new("POLY")
    pts = 9
    spl.points.add(pts - 1)
    altura = ponta.z - (centro.z + RZ * 0.9)
    for i in range(pts):
        a = math.pi * i / (pts - 1)
        spl.points[i].co = (math.cos(a) * RX * 0.85, 0, RZ * 0.9 + math.sin(a) * altura, 1)
    alca_obj = bpy.data.objects.new(f"AlcaCurva.{lado}", curva)
    alca_obj.location = centro
    scene.collection.objects.link(alca_obj)
    dg = bpy.context.evaluated_depsgraph_get()
    me_alca = bpy.data.meshes.new_from_object(alca_obj.evaluated_get(dg))
    bpy.data.objects.remove(alca_obj)
    me_alca.materials.append(M["alca"])
    o = bpy.data.objects.new(f"Alca.{'E' if lado < 0 else 'D'}", me_alca)
    o.location = centro
    colecao.objects.link(o)

# ---------------------------------------------------------------- bolsa nas costas (bolso de jeans + cadarço)
M["jeans"] = material("Jeans", "4E6E98", 0.9)
M["jeans_escuro"] = material("JeansEscuro", "42608A", 0.9)
M["costura_laranja"] = material("CosturaLaranja", "E0781F")
M["cadarco"] = material("Cadarco", "EDEDED", 0.8)
M["latao"] = material("Latao", "C9A227", 0.35)
M["latao"].node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.8

LARG_BOLSA, ALT_BOLSA, PROF_BOLSA = 0.50, 0.38, 0.15
alto, _ = superficie(Vector((0, 0.05, 1.08)), (0, 1, 0))
baixo, _ = superficie(Vector((0, 0.05, 0.74)), (0, 1, 0))
# a bolsa acompanha a inclinação das costas: "cima" vai do ponto de baixo ao de cima
cima = (alto - baixo).normalized()
inclinacao = -math.asin(cima.y)                       # rotação em X que leva +Z para "cima"
fora = Vector((0, math.cos(inclinacao), math.sin(inclinacao)))  # para trás, saindo das costas
centro_bolsa = (alto + baixo) / 2 + fora * (PROF_BOLSA / 2 - 0.01)
rot_bolsa = (math.degrees(inclinacao), 0, 0)


def caixa_arredondada(dims, chanfro):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=dims, verts=bm.verts)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=chanfro, segments=3, affect="EDGES")
    return bm


def na_bolsa(x, altura, saida):
    """Ponto na bolsa: x para o lado, altura a partir do centro, saida para fora da face."""
    return centro_bolsa + Vector((x, 0, 0)) + cima * altura + fora * saida


criar_objeto("Bolsa", caixa_arredondada((LARG_BOLSA, PROF_BOLSA, ALT_BOLSA), 0.035),
             M["jeans"], loc=centro_bolsa, rot=rot_bolsa)
ALT_ABA = ALT_BOLSA * 0.42
criar_objeto("BolsaAba", caixa_arredondada((LARG_BOLSA + 0.012, 0.025, ALT_ABA), 0.01), M["jeans_escuro"],
             loc=na_bolsa(0, ALT_BOLSA / 2 - ALT_ABA / 2 + 0.005, PROF_BOLSA / 2 + 0.006), rot=rot_bolsa)
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.026, radius2=0.026, depth=0.016)
criar_objeto("BolsaBotao", bm, M["latao"], loc=na_bolsa(0, ALT_BOLSA / 2 - ALT_ABA + 0.02, PROF_BOLSA / 2 + 0.022),
             rot=(math.degrees(inclinacao) - 90, 0, 0))

# pesponto laranja: lados e fundo da bolsa, e a borda de baixo da aba
pontos = []
borda_x, borda_baixo, topo_lados = LARG_BOLSA / 2 - 0.04, -ALT_BOLSA / 2 + 0.04, ALT_BOLSA / 2 - ALT_ABA - 0.02
x = -borda_x + 0.02
while x < borda_x:
    pontos.append(((x, borda_baixo), (0.035, 0.012)))
    pontos.append(((x, ALT_BOLSA / 2 - ALT_ABA + 0.035), (0.035, 0.012)))
    x += 0.065
z = borda_baixo + 0.05
while z < topo_lados:
    for lado in (-1, 1):
        pontos.append(((lado * borda_x, z), (0.012, 0.035)))
    z += 0.065
for i, ((x, z), (dx, dz)) in enumerate(pontos):
    saida = PROF_BOLSA / 2 + (0.02 if z > topo_lados else 0.003)
    criar_objeto(f"PontoBolsa.{i}", caixa_arredondada((dx, 0.008, dz), 0.002), M["costura_laranja"],
                 loc=na_bolsa(x, z, saida), rot=rot_bolsa)

# alças de cadarço: saem do topo da bolsa, passam por cima dos ombros, descem pela frente
# e voltam contornando o corpo por baixo das asas até o fundo da bolsa
def pele_de_dentro(miolo, direcao):
    """Ponto onde um raio que sai de DENTRO do corpo atravessa a pele, um pouco para fora."""
    saida, _, _, _ = bvh.ray_cast(miolo, direcao)
    return saida + direcao * 0.015 if saida else None


for lado in (-1, 1):
    trajeto = [na_bolsa(lado * (LARG_BOLSA / 2 - 0.07), ALT_BOLSA / 2 - 0.02, PROF_BOLSA / 2 - 0.02)]
    miolo = Vector((lado * 0.26, 0.02, 0.88))
    for k in range(14):                                 # costas → ombro → desce pela frente
        angulo = math.radians(55 + 175 * k / 13)
        trajeto.append(pele_de_dentro(miolo, Vector((0, math.cos(angulo), math.sin(angulo)))))
    miolo_baixo = Vector((0, 0.05, trajeto[-1].z))
    for k in range(1, 8):                               # frente → lado (embaixo da asa) → costas
        angulo = math.radians(20 + 140 * k / 7)
        trajeto.append(pele_de_dentro(miolo_baixo, Vector((lado * math.sin(angulo), -math.cos(angulo), 0))))
    trajeto = [p for p in trajeto if p is not None]
    trajeto.append(na_bolsa(lado * (LARG_BOLSA / 2 - 0.07), -ALT_BOLSA / 2 + 0.03, PROF_BOLSA / 2 - 0.02))
    curva = bpy.data.curves.new(f"CordaBolsa.{lado}", "CURVE")
    curva.dimensions = "3D"
    curva.bevel_depth = 0.017
    curva.bevel_resolution = 2
    spl = curva.splines.new("POLY")
    spl.points.add(len(trajeto) - 1)
    for ponto, p in zip(spl.points, trajeto):
        ponto.co = (p.x, p.y, p.z, 1)
    obj = bpy.data.objects.new(f"CordaCurva.{lado}", curva)
    scene.collection.objects.link(obj)
    dg = bpy.context.evaluated_depsgraph_get()
    me_corda = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    bpy.data.objects.remove(obj)
    me_corda.materials.append(M["cadarco"])
    colecao.objects.link(bpy.data.objects.new(f"CordaBolsa.{'E' if lado < 0 else 'D'}", me_corda))

# ---------------------------------------------------------------- acabamento suave (esfumado)
# Sombreado liso em tudo; subdivisão só nas partes orgânicas. Pés e pernas ficam retos.
for o in colecao.objects:
    if o.type != "MESH" or o.name.startswith(("Pe.", "Perna", "Costura")):
        continue
    for p in o.data.polygons:
        p.use_smooth = True
    if o.name.startswith(("Corpo", "Asa", "Bico", "PenaRabo", "Olho")):
        sub = o.modifiers.new("Suave", "SUBSURF")
        sub.levels = sub.render_levels = 2

# ---------------------------------------------------------------- cena da folha de ângulos
mundo =bpy.data.worlds.new("Fundo")
scene.world = mundo
try:
    mundo.use_nodes = True
except AttributeError:
    pass
mundo.node_tree.nodes["Background"].inputs["Color"].default_value = linear("15111F")
mundo.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0


def sol(nome, direcao_luz, cor, forca, angulo=8):
    luz = bpy.data.lights.new(nome, "SUN")
    luz.color = linear(cor)[:3]
    luz.energy = forca
    luz.angle = math.radians(angulo)
    o = bpy.data.objects.new(nome, luz)
    scene.collection.objects.link(o)
    o.rotation_euler = (-Vector(direcao_luz)).to_track_quat("-Z", "Y").to_euler()
    return o


sol("LuzPrincipal", (0.6, -1.0, 0.9), "FFF1E0", 3.2)
sol("LuzLua", (-0.9, -0.6, 0.4), "9DB4FF", 1.4)
sol("LuzContraLaranja", (0.4, 1.0, 0.5), "FF8A3A", 4.0)

bpy.context.view_layer.layer_collection.children["Pato"].exclude = True
vistas = [("Frente", -2.75, 0), ("TresQuartos", -0.92, 40), ("Perfil", 0.92, 90), ("Costas", 2.75, 180)]
for nome, x, rz in vistas:
    inst = bpy.data.objects.new(f"Vista{nome}", None)
    inst.instance_type = "COLLECTION"
    inst.instance_collection = colecao
    inst.location = (x, 0, 0)
    inst.rotation_euler = (0, 0, math.radians(rz))
    scene.collection.objects.link(inst)

cam_dados = bpy.data.cameras.new("Camera")
cam_dados.type = "ORTHO"
cam_dados.ortho_scale = 7.4
cam = bpy.data.objects.new("Camera", cam_dados)
cam.location = (0, -12, 2.9)  # um pouco de cima, para os pés aparecerem
cam.rotation_euler = (math.radians(81.5), 0, 0)
scene.collection.objects.link(cam)
scene.camera = cam

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.file_format = "PNG"
try:
    scene.eevee.taa_render_samples = 128
except AttributeError:
    pass

scene.render.filepath = os.path.join(OUT, "renders", "pato_turnaround.png")
bpy.ops.render.render(write_still=True)

# close-up do rosto: câmera em perspectiva olhando a vista frontal
cam_dados.type = "PERSP"
cam_dados.lens = 85
cam.location = (-2.75 + 0.9, -4.2, 1.85)
cam.rotation_euler = (math.radians(88), 0, math.radians(12))
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080
scene.render.filepath = os.path.join(OUT, "renders", "pato_closeup.png")
bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "pato.blend"))
print("PATO_OK", len(colecao.objects), "objetos")
