
from fastapi import APIRouter, Depends, Request
from typing import List
from app.controllers.reaction_controller import create_reaction, get_all_reactions, delete_reaction, get_reactions_for_post
from app.models.reaction import ReactionCreate, ReactionResponse
from app.auth import get_current_user  # adjust if using a different auth setup

router = APIRouter(tags=["Reactions"])

@router.post("/", response_model=ReactionResponse)
def create_reaction_route(
    reaction: ReactionCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a reaction on a post by the current user.
    """
    return create_reaction(reaction, current_user)


@router.get("/", response_model=List[ReactionResponse])
def get_all_reactions_route():
    """
    Retrieve all reactions, including user details (username).
    """
    return get_all_reactions()


@router.delete("/{post_id}")
def delete_reaction_route(post_id: str, current_user: dict = Depends(get_current_user)):
    """
    Delete the current user's reaction on the given post.
    """
    return delete_reaction(post_id, current_user)


@router.get("/post/{post_id}")
def get_reactions_for_post_route(post_id: str, request: Request):
    """Return aggregated reaction counts for a post and the current user's reaction if provided via Bearer token."""
    auth = request.headers.get("authorization")
    token = None
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1]
    return get_reactions_for_post(post_id, token)
