from typing import Annotated

from fastapi import Depends, Request

from eligibilite_livraison.container import AppContainer


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


ContainerDep = Annotated[AppContainer, Depends(get_container)]
