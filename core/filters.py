import math
import time


class _LowPass:
    def __init__(self):
        self.y = None

    def apply(self, x, alpha):
        self.y = x if self.y is None else alpha * x + (1.0 - alpha) * self.y
        return self.y


class OneEuroFilter:
    def __init__(self, min_cutoff=1.4, beta=0.028, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.velocity = 0.0
        self._x_lpf = _LowPass()
        self._dx_lpf = _LowPass()
        self._x_prev = None
        self._t_prev = None

    def reset(self):
        self._x_lpf.y = None
        self._dx_lpf.y = None
        self._x_prev = None
        self._t_prev = None
        self.velocity = 0.0

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x, t=None):
        now = time.perf_counter() if t is None else t
        if self._t_prev is None:
            dt = 1.0 / 30.0
        else:
            dt = max(now - self._t_prev, 1e-6)
        self._t_prev = now

        dx = 0.0 if self._x_prev is None else (x - self._x_prev) / dt
        self._x_prev = x
        edx = self._dx_lpf.apply(dx, self._alpha(self.d_cutoff, dt))
        self.velocity = edx
        cutoff = self.min_cutoff + self.beta * abs(edx)
        return self._x_lpf.apply(x, self._alpha(cutoff, dt))


class FilterPair2D:
    def __init__(self, min_cutoff=1.4, beta=0.028):
        self.fx = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
        self.fy = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
        self.vx = 0.0
        self.vy = 0.0

    @property
    def velocity(self):
        return math.hypot(self.vx, self.vy)

    def set_params(self, min_cutoff, beta):
        for f in (self.fx, self.fy):
            f.min_cutoff = min_cutoff
            f.beta = beta

    def reset(self):
        self.fx.reset()
        self.fy.reset()
        self.vx = 0.0
        self.vy = 0.0

    def filter(self, x, y):
        rx = self.fx.filter(x)
        ry = self.fy.filter(y)
        self.vx = self.fx.velocity
        self.vy = self.fy.velocity
        return rx, ry


class LandmarkFilterBank:
    """Um ``OneEuroFilter`` por coordenada de cada landmark (Onda 1 §1.1).

    Até aqui a palma era o único ponto filtrado, e mesmo essa filtragem acontecia
    a jusante, em ``core/engine.py`` (``E.filters``). Os limiares geométricos que
    decidem pinça, curl, PEACE/ROCK/THREE e o ``thumb_out`` do SHAKA trabalhavam
    sobre as landmarks cruas, ou seja sobre o tremor do detector.

    **Por que o ``min_cutoff`` por omissão é muito mais alto que o da palma** (3.0
    contra 1.4), e isto é deliberado e não uma afinação esquecida:

    * a palma é filtrada **outra vez** a jusante, e esse filtro é o que a
      auto-afinação mexe (``E.filters.set_params``) com a métrica de clique à
      vista. Cascatear os dois com o mesmo cutoff acrescentaria latência ao
      caminho mais sensível do produto — o rato — para ganhar suavidade que a
      palma já tem;
    * filtrar landmarks **junta** latência a cada limiar de gesto, e a decisão de
      pinça já é um Schmitt que faz esse trabalho. A §1.1 manda explicitamente
      "não filtrar a decisão de pinça já triggerizada" e "começar com
      ``min_cutoff`` mais alto que o da palma".

    Com 3.0 a banca é quase transparente em repouso: o ganho de suavidade vem
    do termo ``beta`` quando o ponto se mexe, que é exactamente para isso que o
    One Euro existe.

    Só a ``x``, ``y`` e ``z`` são filtradas. A ``z`` entra porque o próprio
    ``core/gestures.py`` diz que o ``z``-noise do MediaPipe infla o rácio 3D da
    pinça acima do limiar — é o ruido que este filtro existe para tirar.
    """

    def __init__(self, n_points=21, min_cutoff=5.0, beta=0.010, n_dims=3):
        self._filters = [
            [OneEuroFilter(min_cutoff=min_cutoff, beta=beta) for _ in range(n_dims)]
            for _ in range(n_points)
        ]
        self._beta_px = beta
        self._w = self._h = None

    def _apply_scale(self, width, height):
        """Converte ``beta`` de pixels para o espaço normalizado do frame.

        ``OneEuroFilter`` usa ``cutoff = min_cutoff + beta * |edx|``, e ``edx``
        é a velocidade *da coordenada que lhe é passada*. As landmarks do
        MediaPipe vêm normalizadas em [0, 1], mas ``beta`` é herdado de
        ``FilterPair2D``, cujos valores são afinados sobre a palma em **pixels**.
        A diferença não é um factor de estilo, é o filtro inteiro:

            um salto de 32 px em 33 ms mede |edx| = 591.7 /s  ->  beta*|edx| = 5.92 Hz
            o mesmo salto normalizado mede |edx| =   0.925 /s ->  beta*|edx| = 0.0092 Hz

        Em coordenadas normalizadas o termo adaptativo contribui 0.3% do cutoff e
        o One Euro degrada-se num low-pass estático — que é exactamente o que ele
        existe para não ser ("sem tremor parado, sem lag em movimento"). Medido
        no corpus: com ``beta`` sem escala o F1 macro é 0.9098 e a pinça falha
        porque o atraso a leva a não cruzar o limiar do Schmitt a tempo; com
        ``beta`` na escala certa sobe a 1.0000.

        A conversão é uma **multiplicação** pela dimensão, porque normalizar
        divide a coordenada: ``edx_norm = edx_px / width``, logo para que
        ``beta * |edx|`` continue a dar Hz faz falta ``beta_norm = beta_px * width``.
        A ``z`` é normalizada pela **largura** (convenção do MediaPipe), por isso
        partilha a escala de ``x`` e não a de ``y``.
        """
        for row in self._filters:
            row[0].beta = self._beta_px * width
            if len(row) > 1:
                row[1].beta = self._beta_px * height
            if len(row) > 2:
                row[2].beta = self._beta_px * width

    def reset(self):
        """Limpa o estado de todos os filtros.

        Chamado pelo ``GestureEngine.reset()``, que o ``HandPool`` invoca quando a
        mão desaparece. Sem isto, uma mão que sai e volta herda a suavização de
        uma mão que já não está no enquadramento, e o primeiro clique pós-volta
        sai atrasado sem que nada tenha mudado no código.

        O tempo anterior também se perde, e é o ponto: é o que impede a primeira
        frame de calcular uma velocidade a partir de uma posição que já não
        pertence a esta mão.
        """
        for row in self._filters:
            for f in row:
                f.reset()

    def filter(self, landmarks, width, height, t=None):
        """Filtra uma lista de landmarks e devolve tuplos de 3 coordenadas.

        ``width`` e ``height`` são **obrigatórios**, não opcionais com default,
        porque é deles que sai a escala de ``beta`` (ver ``_apply_scale``). Com um
        default de 1 o filtro voltaria a correr na escala normalizada e a falhar
        em silêncio — exactamente o modo de falha que este filtro teve.

        ``t`` e o tempo do frame em segundos. **Envia-o sempre que o caller o
        tenha**: sem ele o filtro usa o relogio de parede, e entao a saida depende
        da velocidade a que o loop corre. Numa camara a 30 fps isso e um detalhe;
        num ``--replay`` que despeja o corpus tao depressa quanto o processador
        permite, ``dt`` e de microssegundos, ``alpha = 1/(1+tau/dt)`` tende a zero
        e o filtro congela. Medido: com o relogio de parede o F1 macro do corpus
        cai de 1.0000 para 0.2787; com o ``t`` do frame volta a 1.0000. E por isso
        que ``dt`` nao pode vir do relogio: um filtro cuja saida depende da
velocidade da maquina nao e um filtro.

        Aceita ``(x, y)`` — preenche a ``z`` a ``0.0``, porque a ``z`` de uma
        detecção a duas dimensões é mesmo zero e inventar um valor seria pior do
        que a ausência. Devolve sempre 3 coordenadas para o consumidor não
        ter de ramificar sobre a forma da entrada.

        Um landmark além de ``n_points`` passa intacto em vez de rebentar: quem
        chama decide o que fazer com uma mão de tamanho inesperado, e um
        ``IndexError`` aqui mataria o loop de vídeo.
        """
        if (width, height) != (self._w, self._h):
            self._apply_scale(width, height)
            self._w, self._h = width, height

        out = []
        for i, lm in enumerate(landmarks):
            row = self._filters[i] if i < len(self._filters) else None
            if row is None:
                out.append(tuple(lm))
                continue
            out.append(tuple(row[d].filter(lm[d] if d < len(lm) else 0.0, t)
                             for d in range(len(row))))
        return out


class AccelCurve:
    """Curva de aceleracao tipo rato gaming.

    expo <= 0 mantem o smoothstep classico; expo > 0 usa curva de potencia
    (t**expo), que e mais precisa devagar e mais agressiva a varrer.
    """

    def __init__(self, min_gain=1.2, max_gain=3.0, ref_speed=1400.0, expo=1.7):
        self.min_gain = float(min_gain)
        self.max_gain = float(max_gain)
        self.ref_speed = max(float(ref_speed), 1e-6)
        self.expo = float(expo)

    def apply(self, vx, vy):
        t = min(math.hypot(vx, vy) / self.ref_speed, 1.0)
        if self.expo > 0.0:
            s = t ** self.expo
        else:
            s = t * t * (3.0 - 2.0 * t)
        return self.min_gain + (self.max_gain - self.min_gain) * s
