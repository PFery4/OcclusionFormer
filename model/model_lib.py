from model.agentformer import AgentFormer
from model.dlow import DLow
from model.original_agentformer import OrigModelWrapper
from model.untrained_models import Oracle, ConstantVelocityPredictor


model_dict = {
    'agentformer': AgentFormer,
    'dlow': DLow,
    'orig_agentformer': OrigModelWrapper,
    'orig_dlow': OrigModelWrapper,
    'oracle': Oracle,
    'const_velocity': ConstantVelocityPredictor
}
