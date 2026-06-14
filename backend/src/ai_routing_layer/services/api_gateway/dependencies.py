from ai_routing_layer.app_state import AppContainer


def get_container() -> AppContainer:
    return AppContainer.instance()
