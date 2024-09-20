from features.commands.types import Command, CommandStage

# Map user id to current command + stage of the command (the handler itself will be index 0, subsequent handling will increment)
user_current_stage: dict[int, CommandStage] = {}


def get_user_current_stage(user_id: int):
    return user_current_stage.get(user_id)


def set_user_current_stage(user_id: int, command: Command, stage: int):
    user_current_stage[user_id] = {"command": command, "stage": stage}


def unset_user_current_stage(user_id: int):
    # Default value just to ignore errors
    user_current_stage.pop(user_id, 0)
