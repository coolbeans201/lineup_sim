"""Streamlit session caches for player pools and scored lineups."""

from __future__ import annotations

import json

import streamlit as st

from lineup_sim.core.models import ScoreResult
from lineup_sim.core.presets import get_preset
from lineup_sim.core.roster import lineup_from_dict, lineup_to_dict
from lineup_sim.core.scoring import score_lineup
from lineup_sim.sports.registry import get_sport_plugin


@st.cache_resource
def load_player_pool_cached(sport: str):
    return get_sport_plugin(sport).load_player_pool()


@st.cache_data(show_spinner=False)
def score_shared_lineup(preset_slug: str, lineup_payload_json: str, sport: str) -> ScoreResult:
    preset = get_preset(preset_slug)
    lineup = lineup_from_dict(preset, json.loads(lineup_payload_json))
    pool = load_player_pool_cached(sport)
    return score_lineup(lineup, pool)


@st.cache_data(show_spinner=False)
def score_lineup_cached(preset_slug: str, lineup_payload_json: str, sport: str) -> ScoreResult:
    preset = get_preset(preset_slug)
    lineup = lineup_from_dict(preset, json.loads(lineup_payload_json))
    pool = load_player_pool_cached(sport)
    return score_lineup(lineup, pool)


def score_lineup_for_ui(lineup) -> ScoreResult:
    payload = json.dumps(lineup_to_dict(lineup), sort_keys=True)
    return score_lineup_cached(lineup.preset_slug, payload, lineup.sport)
