# V23.63.20

Hepsiburada SECURITY_CHALLENGE bounded second recheck.

Scope is intentionally narrow: when the existing Hepsiburada persistent-session product detail path detects a security challenge, it observes the same session after 1 second and, only if still challenged, once more after 2 seconds. It does not solve, bypass, reload-loop, inject cookies, or weaken challenge detection. If real product HTML is not present after both bounded observations, the existing SECURITY_CHALLENGE fail-closed result is preserved. v23.63.19 Idefix, v23.63.16 HB HTTP2 retry, v23.63.15 PttAVM, v23.63.14 Turkcell, price integrity and database continuity are unchanged.
