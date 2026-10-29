def post_init_hook(env):
    """Generate the token signing secret on install if it does not exist yet."""
    env["xtd.ai.token"]._xtd_ai_ensure_secret()
