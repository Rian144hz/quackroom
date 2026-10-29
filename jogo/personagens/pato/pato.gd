## O pato do jogador: anda em 3ª pessoa, pula/plana, agacha e grasna.
## As regras ficam em MovimentoPato e AnimacaoPato (testadas); aqui é a ligação com o Godot.
class_name Pato
extends CharacterBody3D

## Emitido quando o pato grasna. O SomBus (etapa 3) vai transformar isso em onda de sonar.
signal grasnou(forte: bool)

const ACELERACAO := 10.0  ## m/s²: quão rápido o pato chega na velocidade desejada
const VELOCIDADE_PULO := 2.6
const QUEDA_PLANANDO := 0.8  ## segurando Espaço no ar, cai no máximo nessa velocidade
const SENSIBILIDADE_MOUSE := 0.003
const MISTURA_ANIMACAO := 0.15  ## segundos de transição suave entre animações
const ANIMACOES_EM_LOOP: Array[StringName] = [
	&"parado", &"andar_frente", &"andar_tras", &"andar_esquerda", &"andar_direita", &"agachar",
]

var _gravidade: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var _segurando_quack := false
var _tempo_segurando := 0.0
var _grasnando := false

@onready var _pivo_camera: Node3D = $PivoCamera
@onready var _braco_camera: SpringArm3D = $PivoCamera/Braco
@onready var _animacoes: AnimationPlayer = $Modelo/AnimationPlayer


func _ready() -> void:
	for nome in ANIMACOES_EM_LOOP:
		_animacoes.get_animation(nome).loop_mode = Animation.LOOP_LINEAR
	_animacoes.animation_finished.connect(_ao_terminar_animacao)
	_braco_camera.add_excluded_object(get_rid())  # a câmera não "bate" no próprio pato
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _unhandled_input(evento: InputEvent) -> void:
	if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		if evento is InputEventMouseButton and evento.pressed:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED  # clicar na janela volta pro jogo (sem grasnar)
		return

	if evento is InputEventMouseMotion:
		rotate_y(-evento.relative.x * SENSIBILIDADE_MOUSE)  # o pato gira junto com a câmera
		_pivo_camera.rotation.x = clampf(
			_pivo_camera.rotation.x - evento.relative.y * SENSIBILIDADE_MOUSE,
			deg_to_rad(-55.0), deg_to_rad(25.0))
	elif evento.is_action_pressed(&"soltar_mouse"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif evento.is_action_pressed(&"grasnar"):
		_segurando_quack = true
		_tempo_segurando = 0.0
	elif evento.is_action_released(&"grasnar") and _segurando_quack:
		_segurando_quack = false
		_grasnar(MovimentoPato.quack_forte(_tempo_segurando))


func _physics_process(delta: float) -> void:
	if _segurando_quack:
		_tempo_segurando += delta
	var agachado := Input.is_action_pressed(&"agachar")
	var correndo := Input.is_action_pressed(&"correr")

	if not is_on_floor():
		velocity.y -= _gravidade * delta
		if Input.is_action_pressed(&"pular"):
			velocity.y = maxf(velocity.y, -QUEDA_PLANANDO)  # bate as asas e plana
	elif Input.is_action_just_pressed(&"pular") and not agachado:
		velocity.y = VELOCIDADE_PULO

	var entrada := Input.get_vector(&"mover_esquerda", &"mover_direita", &"mover_frente", &"mover_tras")
	var alvo := MovimentoPato.direcao(entrada, rotation.y) * MovimentoPato.velocidade_alvo(correndo, agachado)
	velocity.x = move_toward(velocity.x, alvo.x, ACELERACAO * delta)
	velocity.z = move_toward(velocity.z, alvo.z, ACELERACAO * delta)
	move_and_slide()
	_atualizar_animacao(agachado)


func _atualizar_animacao(agachado: bool) -> void:
	if _grasnando:
		return
	var velocidade_local := global_transform.basis.inverse() * velocity
	var nome := AnimacaoPato.escolher(velocidade_local, is_on_floor(), agachado)
	if nome == &"pular":
		if _animacoes.current_animation != &"pular":
			_animacoes.speed_scale = 1.0
			_animacoes.play(&"pular", MISTURA_ANIMACAO)
			_animacoes.seek(0.3)  # pula a parte de "preparar": a física já tirou o pato do chão
		return
	if _animacoes.current_animation != nome:
		_animacoes.play(nome, MISTURA_ANIMACAO)
	var andando := String(nome).begins_with("andar")
	_animacoes.speed_scale = AnimacaoPato.ritmo(Vector2(velocity.x, velocity.z).length()) if andando else 1.0


func _grasnar(forte: bool) -> void:
	_grasnando = true
	_animacoes.speed_scale = 1.0
	_animacoes.play(&"grasnar", 0.05)
	grasnou.emit(forte)


func _ao_terminar_animacao(nome: StringName) -> void:
	if nome == &"grasnar":
		_grasnando = false
