FINAL_LABELS = ('Engaged', 'Attentive', 'Confused', 'Bored', 'Disengaged')
STATE_CLASSES = ('Bored', 'Confused', 'Drowsy', 'Engaged', 'LookingAway')
ATTENTION_CLASSES = ('HigherAttention', 'LowerAttention')

GEOMETRY_FEATURES = (
    'mean_pitch', 'mean_yaw', 'mean_roll', 'mean_Gh', 'mean_Gv',
)

ATTENTION_FEATURES = (
    'mean_pitch', 'mean_yaw', 'mean_roll', 'mean_Gh', 'mean_Gv',
    'std_pitch', 'std_yaw', 'std_roll', 'std_Gh', 'std_Gv',
)

BLENDSHAPES = (
    'eyeBlinkLeft', 'eyeBlinkRight', 'eyeSquintLeft', 'eyeSquintRight',
    'eyeWideLeft', 'eyeWideRight', 'browDownLeft', 'browDownRight',
    'browInnerUp', 'browOuterUpLeft', 'browOuterUpRight',
    'cheekSquintLeft', 'cheekSquintRight', 'jawOpen', 'mouthFrownLeft',
    'mouthFrownRight', 'mouthSmileLeft', 'mouthSmileRight',
    'mouthPressLeft', 'mouthPressRight',
)

STATE_FEATURES = GEOMETRY_FEATURES + tuple(f'bs_{name}' for name in BLENDSHAPES)


def combine_state(raw_state, attention_state):
    if raw_state in ('Confused', 'Bored'):
        return raw_state
    if raw_state in ('LookingAway', 'Drowsy'):
        return 'Disengaged'
    if raw_state == 'Engaged':
        if attention_state == 'LowerAttention':
            return 'Attentive'
        return 'Engaged'
    return None
