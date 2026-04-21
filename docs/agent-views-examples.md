# `agent-views-examples.md` — Annexe : exemples concrets de construction des vues

> **Annexe de `agent-views.md` (livrable B2).** Exemples de construction des 9 vues agents, conçus comme test-cases de référence pour Phase D. Chaque exemple couvre un `(agent, invocation_trigger)` représentatif et illustre les règles de filtrage, de matérialisation des champs dérivés et d'injection des Windows.

## Objet et usage

Les exemples ci-dessous sont des **snapshots Pydantic complets** tels qu'ils seraient produits par les fonctions `get_xxx_coach_view(state, context)`. Ils servent trois usages :

1. **Référence visuelle** : rendre concrètes les classes Pydantic définies dans `agent-views.md` §4.
2. **Test-cases Phase D** : chaque exemple → un test d'intégration vérifiant que la construction de la vue produit la structure attendue pour des inputs donnés.
3. **Support à la rédaction des prompts Phase C** : les prompts système par agent pourront référencer ces exemples pour démontrer les patterns de lecture attendus (comment l'agent doit interpréter `effective_readiness.resolution`, comment il distingue une vue en mode `baseline` vs `first_personalized`, etc.).

Les exemples utilisent plusieurs athlètes fictifs distincts pour illustrer divers profils : hybride strength/endurance masculin, athlète féminine en cut, etc. Les valeurs numériques sont illustratives.

## Index des exemples

| # | Vue | Trigger | Profil athlète | Situation |
|---|---|---|---|---|
| 1 | `HeadCoachView` | `CHAT_DAILY_CHECKIN` | Hybride H/33 ans | Check-in matinal, override user baisse |
| 2 | `DisciplineCoachView` (Lifting) | `PLAN_GEN_DELEGATE_SPECIALISTS` (block_regen) | Hybride H/33 ans | Régénération bloc 4 d'un plan 12w |
| 3 | `OnboardingCoachDelegationView` | `ONBOARDING_CONDUCT_BLOCK` | Hybride H/33 ans | Phase 2 initiale, bloc OBJECTIVES en cours |
| 4 | `OnboardingCoachConsultationView` | `FOLLOWUP_CONSULT_ONBOARDING` | Hybride H/33 ans | Post-baseline, 3 gaps identifiés sur running |
| 5 | `NutritionCoachView` | `CHAT_WEEKLY_REPORT` | Hybride H/33 ans | Synthèse hebdo, EA LOW_NORMAL avec override user haussier |
| 6 | `RecoveryCoachView` | `RECOVERY_ASSESS_SITUATION` | Hybride H/33 ans | Takeover actif, tendinopathie rotulienne |
| 7 | `EnergyCoachView` | `ESCALATION_NUTRITION_TO_ENERGY` | Femme/32 ans, cut | Pattern RED-S émergent, cycle lutéal tardif |

---

## Exemple 1 — `HeadCoachView` en `CHAT_DAILY_CHECKIN`

### Contexte

Athlète hybride (Lifting FULL + Running FULL + Nutrition FULL + Recovery FULL, Biking en TRACKING). 8h30 un mardi matin, l'utilisateur vient de soumettre son check-in matinal et a coché "je me sens à 65/100" alors que l'HRV et le sommeil calculent objective_readiness à 72.5. Pas de pattern persistent_override_pattern actif, pas d'overlay clinique.

Head Coach doit adapter sa réponse sans moraliser l'override user (baisse autorisée toujours).

### Construction

```python
HeadCoachView(
    view_built_at=datetime(2026, 4, 20, 8, 30),
    invocation_trigger=InvocationTrigger.CHAT_DAILY_CHECKIN,

    ident=HeadCoachIdentView(
        athlete_id="abc-123",
        date_of_birth=date(1992, 6, 15),
        biological_sex="male",
        height_cm=178.0,
        weight_kg=74.2,
        ffm_kg=62.8,
        cycle_active=False,
        cycle_phase=None,
        cycle_day=None,
        cycle_length_days=None,
        timezone="America/Toronto",
        locale="fr-CA",
        unit_preference="metric",
        age_years=33,
    ),
    scope=HeadCoachScopeView(
        coaching_scope={
            Domain.LIFTING: ScopeLevel.FULL,
            Domain.RUNNING: ScopeLevel.FULL,
            Domain.SWIMMING: ScopeLevel.DISABLED,
            Domain.BIKING: ScopeLevel.TRACKING,
            Domain.NUTRITION: ScopeLevel.FULL,
            Domain.RECOVERY: ScopeLevel.FULL,
        },
        peer_disciplines_active=[Discipline.LIFTING, Discipline.RUNNING],
    ),
    journey=HeadCoachJourneyView(
        journey_phase=JourneyPhase.STEADY_STATE,
        recovery_takeover_active=False,
        onboarding_reentry_active=False,
        assessment_mode=False,
    ),
    sub_profiles=HeadCoachSubProfilesView(
        experience_profile=ExperienceProfile(...),      # complet
        objective_profile=ObjectiveProfile(...),         # hybride strength-endurance
        injury_history=InjuryHistory(
            injuries=[
                InjuryRecord(
                    injury_id="inj-chronic-001",
                    region=BodyRegion.KNEE,
                    status=InjuryStatus.CHRONIC_MANAGED,
                    severity=InjurySeverity.MILD,
                    contraindications=[
                        Contraindication(
                            type=ContraindicationType.REDUCE_VOLUME,
                            target="back_squat",
                            notes="Éviter volume > 20 sets/sem",
                        ),
                    ],
                    # ...
                ),
            ],
            has_active_injury=False,
            has_chronic_managed=True,
            last_updated_at=datetime(2026, 1, 10),
        ),
        practical_constraints=PracticalConstraints(...),
    ),
    classification=HeadCoachClassificationView(
        classification={
            Discipline.LIFTING: DimensionClassification(
                capacity=ClassificationLevel.INTERMEDIATE,
                technique=ClassificationLevel.ADVANCED,
                history=ClassificationLevel.ADVANCED,
            ),
            Discipline.RUNNING: DimensionClassification(
                capacity=ClassificationLevel.INTERMEDIATE,
                technique=ClassificationLevel.INTERMEDIATE,
                history=ClassificationLevel.BEGINNER_ADVANCED,
            ),
        },
        confidence_levels={
            (Discipline.LIFTING, ClassificationDimension.CAPACITY): 0.75,
            (Discipline.LIFTING, ClassificationDimension.TECHNIQUE): 0.90,
            (Discipline.LIFTING, ClassificationDimension.HISTORY): 0.95,
            (Discipline.RUNNING, ClassificationDimension.CAPACITY): 0.55,
            (Discipline.RUNNING, ClassificationDimension.TECHNIQUE): 0.70,
            (Discipline.RUNNING, ClassificationDimension.HISTORY): 0.60,
        },
        radar_data=RadarData(...),
        last_classification_update=datetime(2026, 4, 20),
    ),
    plans=HeadCoachPlansView(
        baseline_plan=None,                              # Steady state
        active_plan=ActivePlan(
            plan_id="plan-042",
            status=ActivePlanStatus.ACTIVE,
            # ... blocs, composants, etc.
        ),
    ),
    strain_state=StrainState(
        by_group={
            MuscleGroup.QUADS: MuscleGroupStrain(
                current_value=38.0, peak_24h=45.0, ewma_tau_days=3.0,
                last_contribution_at=datetime(2026, 4, 19, 19, 0),
            ),
            # ... 17 autres groupes
        },
        aggregate=32.0,
        history=[...],
        last_computed_at=datetime(2026, 4, 20, 6, 0),
        recompute_trigger="daily_decay",
    ),
    derived_readiness=HeadCoachDerivedReadinessView(
        objective_readiness=ReadinessValue(
            score=72.5,
            contributing_factors={
                "hrv": 0.30, "sleep": 0.30, "strain": 0.25, "rpe_trend": 0.15,
            },
            computed_at=datetime(2026, 4, 20, 6, 30),
        ),
        user_readiness_signal=UserReadinessSignal(
            score=65.0,
            submitted_at=datetime(2026, 4, 20, 8, 20),
            source="morning_checkin",
        ),
        effective_readiness=EffectiveReadiness(
            score=65.0,
            resolution="user_override_downward",
            user_override_applied=True,
            safeguard_active=None,
        ),
        persistent_override_pattern=PersistentOverridePattern(
            active=False,
            first_detected_at=None,
            consecutive_days_detected=0,
            divergence_magnitude=None,
            set_by=None,
            reset_by=None,
            reset_at=None,
        ),
    ),
    derived_ea=HeadCoachDerivedEAView(
        objective_energy_availability=EnergyAvailabilityValue(
            score=41.5, zone=EAZone.LOW_NORMAL,
            intake_kcal=2820, eee_kcal=215, ffm_kg=62.8,
            computed_at=datetime(2026, 4, 20, 6, 30),
        ),
        user_energy_signal=UserEnergySignal(
            score="neutral", numeric_proxy=0.0,
            submitted_at=datetime(2026, 4, 20, 8, 20),
            source="daily_checkin",
        ),
        effective_energy_availability=EffectiveEA(
            score=41.5, zone=EAZone.LOW_NORMAL,
            resolution="no_user_signal",     # user_energy_signal numeric_proxy=0.0 = neutre, pas d'override
            user_override_applied=False,
            safeguard_active=None,
        ),
    ),
    allostatic_load_state=AllostaticLoadState(
        current_value=48.0,
        zone=AllostaticLoadZone.NORMAL,
        trend_7d_slope=0.1,
        trend_14d_slope=0.2,
        contributing_factors={...},
        history=[...],
        last_computed_at=datetime(2026, 4, 20, 6, 0),
    ),
    technical=HeadCoachTechnicalView(
        active_onboarding_thread_id=None,
        active_plan_generation_thread_id=None,
        active_followup_thread_id=None,
        active_recovery_thread_id=None,
        proactive_messages_last_7d=[],                   # pas de message proactif récent
        connector_status={
            ConnectorName.STRAVA: ConnectorStatus(active=True, last_sync_at=datetime(2026, 4, 20, 5, 30)),
            ConnectorName.HEVY: ConnectorStatus(active=True, last_sync_at=datetime(2026, 4, 19, 20, 0)),
            ConnectorName.APPLE_HEALTH: ConnectorStatus(active=True, last_sync_at=datetime(2026, 4, 20, 7, 0)),
        },
        validation_warnings=[],
    ),
    convo=HeadCoachConvoView(
        last_classified_intent=ClassifiedIntent.DAILY_CHECKIN,
        last_message_at=datetime(2026, 4, 20, 8, 29),
        messages=MessagesWindow(
            scope="current_thread",
            thread_id="abc-123:chat_turn:f47ac10b-a1e4-4f9a-b7c2-001",
            window_start=datetime(2026, 4, 20, 8, 25),
            window_end=datetime(2026, 4, 20, 8, 30),
            messages=[...],                               # 10 messages max, typiquement 3-5 en checkin
            truncated=False,
            total_count_in_window=3,
        ),
    ),
    training_logs={
        Discipline.LIFTING: TrainingLogsRawWindow(
            discipline=Discipline.LIFTING,
            window_start=date(2026, 4, 17),              # 3 jours en checkin
            window_end=date(2026, 4, 20),
            sessions=[
                SessionLogLite(
                    log_id="sess-l-42",
                    discipline=Discipline.LIFTING,
                    session_type="lower_body_strength",
                    session_date=date(2026, 4, 19),
                    duration_minutes=68,
                    volume_realized=VolumeTarget(value=22, unit=VolumeUnit.TOTAL_WORKING_SETS),
                    intensity_realized={"avg_pct_1rm": 0.78},
                    rpe_reported=7.5,
                    prescribed_session_id="presc-l-42",
                    compliance_status="on_plan",
                    strain_contribution_total=10.5,
                    strain_contribution_by_group={
                        MuscleGroup.QUADS: 7.0, MuscleGroup.GLUTES: 3.5,
                    },
                    notes=None,
                    exercise_details=None,               # Head Coach n'a pas hydrate_exercise_details
                    interval_details=None,
                ),
            ],
            total_sessions_count=1,
            total_volume_realized=VolumeTarget(value=22, unit=VolumeUnit.TOTAL_WORKING_SETS),
            avg_rpe=7.5,
            compliance_rate=1.0,
            last_session_at=datetime(2026, 4, 19, 19, 30),
            coverage_rate=1.0,
        ),
        Discipline.RUNNING: TrainingLogsRawWindow(
            discipline=Discipline.RUNNING,
            window_start=date(2026, 4, 17),
            window_end=date(2026, 4, 20),
            sessions=[
                SessionLogLite(
                    log_id="sess-r-28",
                    discipline=Discipline.RUNNING,
                    session_type="easy_run",
                    session_date=date(2026, 4, 18),
                    duration_minutes=45,
                    volume_realized=VolumeTarget(value=8.5, unit=VolumeUnit.KILOMETERS),
                    intensity_realized={"zone_2_ratio": 0.95},
                    rpe_reported=4.5,
                    prescribed_session_id="presc-r-28",
                    compliance_status="on_plan",
                    strain_contribution_total=4.0,
                    strain_contribution_by_group={MuscleGroup.QUADS: 2.0, MuscleGroup.CALVES: 1.5},
                    notes=None,
                    exercise_details=None,
                    interval_details=None,
                ),
            ],
            total_sessions_count=1,
            total_volume_realized=VolumeTarget(value=8.5, unit=VolumeUnit.KILOMETERS),
            avg_rpe=4.5,
            compliance_rate=1.0,
            last_session_at=datetime(2026, 4, 18, 6, 45),
            coverage_rate=1.0,
        ),
    },
    training_logs_tracking={
        Discipline.BIKING: TrainingLogsRawWindow(
            discipline=Discipline.BIKING,
            window_start=date(2026, 4, 13),              # fenêtre tracking fixe 7j
            window_end=date(2026, 4, 20),
            sessions=[],                                  # aucun ride récent
            total_sessions_count=0,
            total_volume_realized=None,
            avg_rpe=None,
            compliance_rate=None,
            last_session_at=None,
            coverage_rate=1.0,
        ),
    },
    physio_logs=PhysioLogsWindow(
        window_start=date(2026, 4, 17),                  # 3 jours raw en checkin
        window_end=date(2026, 4, 20),
        format="raw",
        daily_points=[
            DailyPhysioPoint(
                date=date(2026, 4, 18),
                hrv_rmssd_ms=52.0, hrv_deviation_z_score=-0.2,
                sleep_duration_hours=7.8, sleep_quality_score=82,
                resting_heart_rate_bpm=54, weight_kg=74.0,
                subjective_stress="low", subjective_energy="high",
                morning_checkin_submitted=True,
            ),
            DailyPhysioPoint(
                date=date(2026, 4, 19),
                hrv_rmssd_ms=48.5, hrv_deviation_z_score=-0.6,
                sleep_duration_hours=6.5, sleep_quality_score=68,
                resting_heart_rate_bpm=57, weight_kg=74.2,
                subjective_stress="moderate", subjective_energy="neutral",
                morning_checkin_submitted=True,
            ),
            DailyPhysioPoint(
                date=date(2026, 4, 20),
                hrv_rmssd_ms=49.0, hrv_deviation_z_score=-0.5,
                sleep_duration_hours=7.0, sleep_quality_score=72,
                resting_heart_rate_bpm=56, weight_kg=74.2,
                subjective_stress="moderate", subjective_energy="low",
                morning_checkin_submitted=True,
            ),
        ],
        summary=PhysioLogsSummary(
            hrv_trend_slope_per_day=-0.8,
            hrv_deviations_count=0,
            hrv_last_value=49.0,
            sleep_avg_hours=7.1,
            sleep_debt_cumulative_hours=-2.7,
            sleep_last_quality=72.0,
            rhr_trend_slope_per_day=0.7,
            weight_trend_slope_per_week_kg=0.1,
            last_log_at=datetime(2026, 4, 20, 7, 0),
            coverage_rate=1.0,
        ),
    ),
    nutrition_logs=NutritionLogsWindow(
        window_start=date(2026, 4, 17),
        window_end=date(2026, 4, 20),
        format="raw",
        daily_points=[...],                               # 3 jours, adherence ~95%
        summary=NutritionLogsSummary(
            avg_calories_kcal=2810, avg_protein_g=175, avg_carbs_g=320, avg_fat_g=88,
            adherence_rate=0.95, days_with_log_count=3, coverage_rate=1.0,
            last_log_at=datetime(2026, 4, 19, 20, 30),
        ),
    ),
)
```

### Lecture attendue par Head Coach

`effective_readiness.score=65.0` avec `resolution="user_override_downward"` signale que l'utilisateur a reporté se sentir moins bien que ce que les métriques objectives indiquent. Posture attendue : réponse qui accuse réception du check-in, propose éventuellement d'alléger la séance du jour si elle était prévue intense, **sans force-override à la hausse**. Sleep a baissé (6.5h avant-hier, 7.0h hier), stress modéré monté : explications plausibles que le user ressent.

`effective_ea.zone=LOW_NORMAL` signale un déficit marginal persistant mais pas critique. Pas d'escalade ; juste à contextualiser si le user demande conseil sur la nutrition.

`training_logs_tracking[BIKING]` vide : pas d'info exploitable côté biking, rien à signaler.

---

## Exemple 2 — `DisciplineCoachView` (Lifting) en `PLAN_GEN_DELEGATE_SPECIALISTS` (block_regen)

### Contexte

Même athlète hybride H/33 ans. Le bloc 3 (Peak strength, 2026-04-09 → 2026-04-28) arrive à terme. Le Coordinator invoque `plan_generation` en mode `block_regen` pour générer le bloc 4. `delegate_specialists` appelle en parallèle Lifting Coach, Running Coach, Nutrition Coach, Energy Coach. Voici ce que le Lifting Coach voit.

### Construction

```python
DisciplineCoachView(
    view_built_at=datetime(2026, 4, 21, 10, 15),
    invocation_trigger=InvocationTrigger.PLAN_GEN_DELEGATE_SPECIALISTS,
    target_discipline=Discipline.LIFTING,
    generation_mode="block_regen",

    ident=DisciplineCoachIdentView(
        date_of_birth=date(1992, 6, 15),
        biological_sex="male",
        height_cm=178.0,
        weight_kg=74.2,
        ffm_kg=62.8,
        cycle_active=False,
        cycle_phase=None,
        age_years=33,
    ),
    scope=DisciplineCoachScopeView(
        target_discipline_scope=ScopeLevel.FULL,
        peer_disciplines_active=[Discipline.RUNNING],    # target Lifting exclu
    ),
    journey=DisciplineCoachJourneyView(
        journey_phase=JourneyPhase.STEADY_STATE,
        assessment_mode=False,
    ),
    sub_profiles=DisciplineCoachSubProfilesView(
        objective_profile=ObjectiveProfile(
            primary=Objective(
                category=ObjectiveCategory.HYBRID_STRENGTH_ENDURANCE,
                priority=ObjectivePriority.PRIMARY,
                horizon=ObjectiveHorizon.MEDIUM,
                target_date=date(2026, 10, 15),
                target_metric=TargetMetric(
                    metric_name="half_marathon_time",
                    current_value=6000,          # 1h40
                    target_value=5700,           # 1h35
                    unit="sec",
                ),
                free_text_description="Semi sous 1h35 tout en gardant 140kg squat",
                declared_at=datetime(2026, 1, 10),
            ),
            secondary=[],
            trade_offs_acknowledged=[],
            last_revision_at=datetime(2026, 1, 10),
            revision_count=0,
        ),
        discipline_experience=DisciplineExperience(
            years_structured=8.5,
            typical_frequency_per_week_12m=4.0,
            prs_referenced=[
                PRRecord(movement_or_distance="back_squat", value=140, unit="kg", ...),
                PRRecord(movement_or_distance="deadlift", value=180, unit="kg", ...),
                PRRecord(movement_or_distance="bench_press", value=105, unit="kg", ...),
            ],
            movements_mastered=["back_squat", "deadlift", "bench_press", "overhead_press",
                                "front_squat", "romanian_deadlift", "pull_up"],
            distances_covered=[],
            weekly_volume_recent_8w=VolumeRecord(value=18, unit="total_working_sets"),
            longest_session_recent_8w=SessionExtremeRecord(
                value=95, unit="minutes", approximate_date=date(2026, 4, 5),
            ),
            most_intense_session_recent_8w=SessionExtremeRecord(
                value=127.5, unit="kg_load", approximate_date=date(2026, 4, 12),
            ),
            relative_charges={
                "back_squat": 1.89, "deadlift": 2.43, "bench_press": 1.42,
            },
            bloc_marked_insufficient=False,
        ),
        practical_constraints=PracticalConstraints(...),     # complet
        injury_history_filtered=DisciplineFilteredInjuryHistory(
            target_discipline=Discipline.LIFTING,
            relevant_injuries=[
                InjuryRecord(
                    injury_id="inj-chronic-001",
                    region=BodyRegion.KNEE,
                    status=InjuryStatus.CHRONIC_MANAGED,
                    severity=InjurySeverity.MILD,
                    contraindications=[
                        Contraindication(
                            type=ContraindicationType.REDUCE_VOLUME,
                            target="back_squat",
                            notes="Éviter volume > 20 sets/semaine",
                        ),
                    ],
                    # ...
                ),
            ],
            has_active_injury_impacting_discipline=False,
            has_chronic_impacting_discipline=True,
            has_avoid_discipline_contraindication=False,
            filtered_at=datetime(2026, 4, 21, 10, 15),
            impact_table_version="1.0.0",
        ),
    ),
    classification=DisciplineCoachClassificationView(
        target_discipline_classification=DimensionClassification(
            capacity=ClassificationLevel.INTERMEDIATE,
            technique=ClassificationLevel.ADVANCED,
            history=ClassificationLevel.ADVANCED,
        ),
        target_discipline_confidence={
            ClassificationDimension.CAPACITY: 0.75,
            ClassificationDimension.TECHNIQUE: 0.90,
            ClassificationDimension.HISTORY: 0.95,
        },
    ),
    plans=DisciplineCoachPlansView(
        active_plan_blocks=[
            PlanBlock(id="b1", title="Accumulation", theme="accumulation",
                      start_date=date(2026, 1, 15), end_date=date(2026, 2, 11),
                      status=BlockStatus.COMPLETED, detail_level=BlockDetailLevel.SUMMARY,
                      block_discipline_specs=None, actual_compliance_rate=0.95),
            PlanBlock(id="b2", title="Intensification", theme="intensification",
                      start_date=date(2026, 2, 12), end_date=date(2026, 3, 11),
                      status=BlockStatus.COMPLETED, detail_level=BlockDetailLevel.SUMMARY,
                      block_discipline_specs=None, actual_compliance_rate=0.92),
            PlanBlock(id="b3", title="Peak strength", theme="peaking",
                      start_date=date(2026, 4, 9), end_date=date(2026, 4, 28),
                      status=BlockStatus.CURRENT, detail_level=BlockDetailLevel.FULL,
                      block_discipline_specs={                 # bloc courant, spec discipline visible
                          Discipline.LIFTING: BlockDisciplineSpec(
                              discipline=Discipline.LIFTING,
                              weekly_volume_target=VolumeTarget(value=18, unit=VolumeUnit.TOTAL_WORKING_SETS),
                              intensity_distribution=IntensityDistribution(
                                  zones={"heavy_85_plus": 0.40, "moderate_70_85": 0.45, "light_under_70": 0.15},
                              ),
                              key_sessions_per_week=3,
                              block_theme_for_discipline="peak_strength_lower_upper_split",
                              prescribed_session_ids=[...],
                          ),
                          # discipline_specs[RUNNING] MASQUÉ — isolation par discipline
                      },
                      actual_compliance_rate=0.93),
        ],
        active_plan_target_component=PlanComponent(
            discipline=Discipline.LIFTING,
            role_in_plan=DisciplineRoleInPlan.CO_PRIMARY,
            total_volume_arc=[
                WeeklyVolumePoint(week_number=1, volume=VolumeTarget(value=16, unit=VolumeUnit.TOTAL_WORKING_SETS)),
                # ... 12 semaines
            ],
            peak_block_id="b3",
            deload_block_ids=[],
            projected_strain_cap=55.0,
            deprioritized_vs_ideal=False,
            deprioritization_rationale=None,
        ),
        active_plan_trade_offs_relevant=[
            TradeOff(
                category=TradeOffCategory.VOLUME_DEPRIORITIZED,
                sacrificed_element="lifting_accessory_volume",
                protected_element="running_intensity_key_sessions",
                rationale="Objectif hybride : préserver capacité aérobie de pointe, "
                          "accepter volume lifting sous landmark MAV",
                magnitude="moderate",
                disclosed_at=datetime(2026, 1, 15),
                disclosed_in_plan_id="plan-042",
                acknowledged_by_user=True,
                acknowledged_at=datetime(2026, 1, 15),
            ),
        ],
        active_plan_status=ActivePlanStatus.ACTIVE,
        active_plan_generated_at=datetime(2026, 1, 15),
        active_plan_horizon=PlanHorizon.TWELVE_WEEKS,
        baseline_plan_summary=None,                       # block_regen : masqué
    ),
    derived=DisciplineCoachDerivedView(
        strain_state=StrainStateWithoutOrigin(
            by_group={
                MuscleGroup.QUADS: MuscleGroupStrainWithoutOrigin(
                    current_value=48.0, peak_24h=62.0, ewma_tau_days=3.0,
                    # last_contribution_at MASQUÉ
                ),
                MuscleGroup.HAMSTRINGS: MuscleGroupStrainWithoutOrigin(
                    current_value=35.0, peak_24h=42.0, ewma_tau_days=3.0,
                ),
                # ... 16 autres groupes
            },
            aggregate=38.5,
            history=[...],                                # 21 points
            last_computed_at=datetime(2026, 4, 21, 6, 0),
            recompute_trigger="daily_decay",
        ),
        effective_readiness=EffectiveReadiness(
            score=68.0, resolution="user_override_downward",
            user_override_applied=True, safeguard_active=None,
        ),
        effective_energy_availability=EffectiveEA(
            score=42.0, zone=EAZone.LOW_NORMAL,
            resolution="no_user_signal",
            user_override_applied=False, safeguard_active=None,
        ),
        allostatic_load_state=AllostaticLoadState(
            current_value=52.0, zone=AllostaticLoadZone.NORMAL,
            trend_7d_slope=0.3, trend_14d_slope=0.5,
            contributing_factors={...},
            history=[...],
            last_computed_at=datetime(2026, 4, 21, 6, 0),
        ),
    ),
    training_logs=TrainingLogsRawWindow(
        discipline=Discipline.LIFTING,                    # isolation stricte
        window_start=date(2026, 3, 10),                   # 42 jours
        window_end=date(2026, 4, 20),
        sessions=[
            SessionLogLite(
                log_id="sess-l-40",
                discipline=Discipline.LIFTING,
                session_type="lower_body_strength",
                session_date=date(2026, 4, 18),
                duration_minutes=72,
                volume_realized=VolumeTarget(value=24, unit=VolumeUnit.TOTAL_WORKING_SETS),
                intensity_realized={"avg_pct_1rm": 0.82},
                rpe_reported=8.5,
                prescribed_session_id="presc-l-40",
                compliance_status="on_plan",
                strain_contribution_total=12.5,
                strain_contribution_by_group={
                    MuscleGroup.QUADS: 8.0, MuscleGroup.HAMSTRINGS: 3.5, MuscleGroup.GLUTES: 4.0,
                },
                notes="Série finale ratée 1 rep",
                exercise_details=[                        # HYDRATÉ car Lifting Coach propriétaire
                    ExerciseLog(
                        exercise_name="back_squat",
                        exercise_category="squat",
                        prescribed=True,
                        substitution_of=None,
                        sets=[
                            SetLog(set_number=1, reps_prescribed=5, reps_realized=5,
                                   load_kg=100, rpe_reported=6.5, rest_seconds=180),
                            SetLog(set_number=2, reps_prescribed=5, reps_realized=5,
                                   load_kg=110, rpe_reported=7.5, rest_seconds=180),
                            SetLog(set_number=3, reps_prescribed=5, reps_realized=5,
                                   load_kg=120, rpe_reported=8.5, rest_seconds=240),
                            SetLog(set_number=4, reps_prescribed=5, reps_realized=4,
                                   load_kg=125, rpe_reported=9.5, rest_seconds=240, completed=True),
                        ],
                    ),
                    ExerciseLog(
                        exercise_name="romanian_deadlift",
                        exercise_category="hinge",
                        prescribed=True,
                        sets=[
                            SetLog(set_number=1, reps_prescribed=8, reps_realized=8,
                                   load_kg=80, rpe_reported=7.0),
                            # ... 3 autres séries
                        ],
                    ),
                    # ... accessoires
                ],
                interval_details=None,
            ),
            # ... ~18 séances sur 42 jours à ~3/semaine
        ],
        total_sessions_count=18,
        total_volume_realized=VolumeTarget(value=420, unit=VolumeUnit.TOTAL_WORKING_SETS),
        avg_rpe=7.8,
        compliance_rate=0.92,
        last_session_at=datetime(2026, 4, 18, 19, 30),
        coverage_rate=0.98,
    ),
    physio_logs=PhysioLogsWindow(
        window_start=date(2026, 4, 7),                    # 14 jours summary_only
        window_end=date(2026, 4, 20),
        format="summary_only",
        daily_points=None,
        summary=PhysioLogsSummary(
            hrv_trend_slope_per_day=-0.3,
            hrv_deviations_count=2,
            hrv_last_value=48.5,
            sleep_avg_hours=7.2,
            sleep_debt_cumulative_hours=-3.5,
            sleep_last_quality=72.0,
            rhr_trend_slope_per_day=0.1,
            weight_trend_slope_per_week_kg=-0.2,
            last_log_at=datetime(2026, 4, 20, 7, 0),
            coverage_rate=0.93,
        ),
    ),
)
```

### Lecture attendue par Lifting Coach

Le bloc 3 "Peak strength" se termine dans 7 jours avec compliance 93%. `exercise_details` sur la dernière séance montre que la série finale à 125kg×4 a été proche de l'échec (RPE 9.5, reps prescribed 5 réalisées 4) — signal de fatigue accumulée. `strain_state.aggregate=38.5` et `quads.current_value=48.0` : accumulation significative mais sous seuil critique. `effective_readiness=68` avec override user downward.

Le trade-off `VOLUME_DEPRIORITIZED` acknowledge rappelle que le Lifting est en co-primary avec Running, volume sous landmark MAV accepté. Confidence classification CAPACITY=0.75 (moyenne), TECHNIQUE=0.90 et HISTORY=0.95 (forts).

Décision attendue : `Recommendation` (contrat B3) pour un bloc 4 de type **deload ou transition** (après Peak strength vient typiquement consolidation ou recul volume). Prescription avec réduction volume -30% première semaine, intensité maintenue, focus récupération pour préparer cycle suivant. `flag_for_head_coach` peut signaler "bloc Peak complété avec signes fatigue, propose deload bloc 4". Signal genou chronique dans contraindications : éviter volume back_squat > 20 sets/sem, respecté par proposition.

---

## Exemple 3 — `OnboardingCoachDelegationView` en `ONBOARDING_CONDUCT_BLOCK`

### Contexte

Même athlète hybride H/33 ans, mais ici en **Phase 2 onboarding initiale**, 3 mois plus tôt (14h32 le 21 janvier 2026). L'Onboarding Coach détient le tour conversationnel. Le bloc OBJECTIVES est en cours, c'est le premier bloc du parcours. Aucun sous-profil n'est encore construit (tous None sauf `injury_history` qui est présent avec liste vide par défaut).

### Construction

```python
OnboardingCoachDelegationView(
    view_built_at=datetime(2026, 1, 21, 14, 32),
    invocation_trigger=InvocationTrigger.ONBOARDING_CONDUCT_BLOCK,
    is_reentry=False,

    blocks_to_cover=[
        OnboardingBlockType.OBJECTIVES,
        OnboardingBlockType.EXPERIENCE,
        OnboardingBlockType.INJURIES,
        OnboardingBlockType.CONSTRAINTS,
        OnboardingBlockType.IDENT_REFINEMENT,
    ],
    current_block=OnboardingBlockType.OBJECTIVES,
    blocks_already_completed=[],                          # premier bloc
    current_onboarding_thread_id="abc-123:onboarding:f47ac10b-a1e4-4f9a-b7c2-001",

    ident=OnboardingDelegationIdentView(
        date_of_birth=date(1992, 6, 15),
        biological_sex="male",
        height_cm=178.0,
        weight_kg=74.2,
        ffm_kg=None,                                      # pas encore raffinée
        cycle_active=False,
        age_years=33,
        # cycle_phase, cycle_day, cycle_length_days MASQUÉS en Delegation
    ),
    scope=OnboardingDelegationScopeView(
        coaching_scope={
            Domain.LIFTING: ScopeLevel.FULL,
            Domain.RUNNING: ScopeLevel.FULL,
            Domain.SWIMMING: ScopeLevel.DISABLED,
            Domain.BIKING: ScopeLevel.DISABLED,            # pas encore en TRACKING à ce stade
            Domain.NUTRITION: ScopeLevel.FULL,
            Domain.RECOVERY: ScopeLevel.FULL,
        },
        peer_disciplines_active=[Discipline.LIFTING, Discipline.RUNNING],
    ),
    journey=OnboardingDelegationJourneyView(
        journey_phase=JourneyPhase.ONBOARDING,
        is_reentry=False,
    ),
    sub_profiles=OnboardingDelegationSubProfilesView(
        experience_profile=None,                          # pas encore construit
        objective_profile=None,                           # bloc en cours
        injury_history=InjuryHistory(
            injuries=[],
            has_active_injury=False,
            has_chronic_managed=False,
            last_updated_at=datetime(2026, 1, 21, 14, 30),
        ),
        practical_constraints=None,
    ),
    messages=MessagesWindow(
        scope="current_thread",
        thread_id="abc-123:onboarding:f47ac10b-a1e4-4f9a-b7c2-001",
        window_start=datetime(2026, 1, 21, 14, 25),
        window_end=datetime(2026, 1, 21, 14, 32),
        messages=[
            MessageLite(
                message_id="msg-1",
                thread_id="abc-123:onboarding:f47ac10b-a1e4-4f9a-b7c2-001",
                timestamp=datetime(2026, 1, 21, 14, 25),
                author="onboarding_coach",
                content="Avant de concevoir ton plan, j'ai besoin de cerner ce que tu cherches. "
                        "Sur les 6 à 12 prochains mois, qu'est-ce qui compterait vraiment pour toi "
                        "côté training ?",
            ),
            MessageLite(
                message_id="msg-2",
                thread_id="abc-123:onboarding:f47ac10b-a1e4-4f9a-b7c2-001",
                timestamp=datetime(2026, 1, 21, 14, 27),
                author="user",
                content="Je veux améliorer mon semi sous 1h35 tout en gardant ma force au squat.",
                classified_intent=None,
            ),
            MessageLite(
                message_id="msg-3",
                thread_id="abc-123:onboarding:f47ac10b-a1e4-4f9a-b7c2-001",
                timestamp=datetime(2026, 1, 21, 14, 30),
                author="onboarding_coach",
                content="Compris. Tu parles de deux choses simultanément — un objectif endurance "
                        "chiffré, et un seuil de force à préserver. Ton PR actuel au squat, tu "
                        "l'évalues autour de combien ?",
            ),
        ],
        truncated=False,
        total_count_in_window=3,
    ),
)
```

### Lecture attendue par Onboarding Coach

L'agent est au milieu du bloc OBJECTIVES, premier bloc du parcours. Il vient d'obtenir un objectif déclaratif hybride (semi 1h35 + squat préservé). Tous les autres sous-profils sont `None` — normal, bloc pas encore atteint. Signal : l'utilisateur formule son objectif sous forme d'optimisation sous contrainte ("X tout en gardant Y"), indication de maturité de pensée.

Décision attendue pour le prochain tour : continuer à élucider les paramètres numériques (target_date, target_value, unit), poser éventuellement une question sur le niveau de 1RM actuel pour calibrer le "garder" (maintenance vs progression lente). Ne pas déborder sur l'expérience running (bloc EXPERIENCE à venir). Ne pas mentionner de plan (pas encore en Phase 3).

Persistance : quand le bloc sera complété, le node `persist_block` écrira l'`ObjectiveProfile` sur l'athlete state, avec `primary` hybride strength/endurance. Puis `advance_to_next_block` → EXPERIENCE.

---

## Exemple 4 — `OnboardingCoachConsultationView` en `FOLLOWUP_CONSULT_ONBOARDING`

### Contexte

Même athlète hybride H/33 ans, **Phase 5** (followup_transition). 9h00 le 5 mai 2026. L'onboarding initial a été complété en janvier, le plan baseline a tourné du 21 avril au 4 mai, la baseline est terminée et les exit_conditions remplies. Le node `compare_declarative_vs_observed` a identifié 3 gaps, tous sur la discipline Running. L'Onboarding Coach est consulté pour générer des questions ciblées que Head Coach posera ensuite.

### Construction

```python
OnboardingCoachConsultationView(
    view_built_at=datetime(2026, 5, 5, 9, 0),
    invocation_trigger=InvocationTrigger.FOLLOWUP_CONSULT_ONBOARDING,

    ident=OnboardingConsultationIdentView(
        date_of_birth=date(1992, 6, 15),
        biological_sex="male",
        height_cm=178.0,
        weight_kg=74.5,
        ffm_kg=63.1,                                      # raffinée depuis onboarding
        cycle_active=False,
        cycle_phase=None,
        age_years=33,
    ),
    scope=OnboardingConsultationScopeView(
        coaching_scope={
            Domain.LIFTING: ScopeLevel.FULL,
            Domain.RUNNING: ScopeLevel.FULL,
            Domain.SWIMMING: ScopeLevel.DISABLED,
            Domain.BIKING: ScopeLevel.TRACKING,            # ajouté entre temps
            Domain.NUTRITION: ScopeLevel.FULL,
            Domain.RECOVERY: ScopeLevel.FULL,
        },
        peer_disciplines_active=[Discipline.LIFTING, Discipline.RUNNING],
    ),
    journey=OnboardingConsultationJourneyView(
        journey_phase=JourneyPhase.FOLLOWUP_TRANSITION,
        assessment_mode=True,
    ),
    sub_profiles=OnboardingConsultationSubProfilesView(
        experience_profile=ExperienceProfile(
            by_discipline={
                Discipline.LIFTING: DisciplineExperience(
                    years_structured=8.5,
                    typical_frequency_per_week_12m=4.0,
                    weekly_volume_recent_8w=VolumeRecord(value=130, unit="total_working_sets"),
                    relative_charges={"back_squat": 1.89, "deadlift": 2.43},
                    # ...
                ),
                Discipline.RUNNING: DisciplineExperience(
                    years_structured=3.0,
                    typical_frequency_per_week_12m=4.0,
                    # Déclaratif ONBOARDING : "50-60km/semaine, capable de tenir 4:30/km sur 10km"
                    weekly_volume_recent_8w=VolumeRecord(value=55, unit="km"),
                    # ...
                ),
            },
            last_updated_at=datetime(2026, 1, 25),
            last_updated_by="onboarding_coach",
        ),
        objective_profile=ObjectiveProfile(
            primary=Objective(
                category=ObjectiveCategory.HYBRID_STRENGTH_ENDURANCE,
                priority=ObjectivePriority.PRIMARY,
                horizon=ObjectiveHorizon.MEDIUM,
                target_date=date(2026, 10, 15),
                target_metric=TargetMetric(
                    metric_name="half_marathon_time",
                    current_value=6000, target_value=5700, unit="sec",
                ),
                declared_at=datetime(2026, 1, 21),
            ),
            secondary=[],
            trade_offs_acknowledged=[],
            last_revision_at=datetime(2026, 1, 21),
            revision_count=0,
        ),
        injury_history=InjuryHistory(
            injuries=[
                InjuryRecord(
                    injury_id="inj-chronic-001",
                    region=BodyRegion.KNEE,
                    status=InjuryStatus.CHRONIC_MANAGED,
                    severity=InjurySeverity.MILD,
                    # déclarée en onboarding initial
                    # ...
                ),
            ],
            has_active_injury=False,
            has_chronic_managed=True,
            last_updated_at=datetime(2026, 1, 25),
        ),
        practical_constraints=PracticalConstraints(...),  # complet
    ),
    classification=OnboardingConsultationClassificationView(
        classification={
            Discipline.LIFTING: DimensionClassification(
                capacity=ClassificationLevel.INTERMEDIATE,
                technique=ClassificationLevel.ADVANCED,
                history=ClassificationLevel.ADVANCED,
            ),
            Discipline.RUNNING: DimensionClassification(
                capacity=ClassificationLevel.INTERMEDIATE,
                technique=ClassificationLevel.INTERMEDIATE,
                history=ClassificationLevel.BEGINNER_ADVANCED,
            ),
        },
        confidence_levels={
            (Discipline.LIFTING, ClassificationDimension.CAPACITY): 0.75,
            (Discipline.LIFTING, ClassificationDimension.TECHNIQUE): 0.90,
            (Discipline.LIFTING, ClassificationDimension.HISTORY): 0.95,
            (Discipline.RUNNING, ClassificationDimension.CAPACITY): 0.55,    # faible
            (Discipline.RUNNING, ClassificationDimension.TECHNIQUE): 0.70,
            (Discipline.RUNNING, ClassificationDimension.HISTORY): 0.60,
        },
        last_classification_update=datetime(2026, 1, 25),
    ),

    baseline_observations=BaselineObservations(
        baseline_plan_id="baseline-xyz-789",
        baseline_window_start=date(2026, 4, 21),
        baseline_window_end=date(2026, 5, 4),
        compliance_rate=0.93,
        sessions_representative_count=12,
        sufficient_data_for_analysis=True,
        actual_vs_prescribed_volume_ratio={
            Discipline.LIFTING: 0.95,                     # très proche du prescrit
            Discipline.RUNNING: 0.72,                     # sous le prescrit
        },
        actual_vs_prescribed_intensity_ratio={
            Discipline.LIFTING: 1.02,
            Discipline.RUNNING: 1.15,                     # intensité plus haute que prescrit
        },
        avg_rpe_vs_prescribed={
            Discipline.LIFTING: 0.95,                     # RPE ≈ prescrit
            Discipline.RUNNING: 1.3,                      # RPE significativement au-dessus du prescrit
        },
        gaps=[
            DeclarativeVsObservedGap(
                dimension="volume_tolerance",
                discipline=Discipline.RUNNING,
                targeted_classification_dimension=ClassificationDimension.CAPACITY,
                declared_snapshot="50-60km/semaine déclarés comme volume habituel",
                observed_snapshot="Volume réalisé 36-42km/semaine sur baseline 14j",
                gap_magnitude="significant_gap",
                supporting_evidence_session_ids=["sess-r-1", "sess-r-3", "sess-r-5"],
                supporting_evidence_summary="3 séances raccourcies vs prescrit, "
                                            "aucune blessure rapportée, raccourcies volontairement",
            ),
            DeclarativeVsObservedGap(
                dimension="intensity_tolerance",
                discipline=Discipline.RUNNING,
                targeted_classification_dimension=ClassificationDimension.CAPACITY,
                declared_snapshot="Allure cible déclarée 4:30/km sur 10km (VDOT ≈ 52)",
                observed_snapshot="RPE moyen 8.5 sur séances tempo à 4:45/km "
                                  "(intensité plus élevée que l'allure ne le laisse penser)",
                gap_magnitude="significant_gap",
                supporting_evidence_session_ids=["sess-r-2", "sess-r-4", "sess-r-7"],
                supporting_evidence_summary="RPE systématiquement >8 sur tempo, "
                                            "tendance à surévaluer l'allure soutenable",
            ),
            DeclarativeVsObservedGap(
                dimension="pacing_discipline",
                discipline=Discipline.RUNNING,
                targeted_classification_dimension=ClassificationDimension.TECHNIQUE,
                declared_snapshot="Expérience 3 ans running structuré",
                observed_snapshot="Départs trop rapides sur 2/3 des sessions longues "
                                  "(pace split 1 - pace moyenne > 15s/km)",
                gap_magnitude="minor_gap",
                supporting_evidence_session_ids=["sess-r-6", "sess-r-8"],
                supporting_evidence_summary="Pacing inégal, signal maturité d'entraînement limitée",
            ),
        ],
        generated_at=datetime(2026, 5, 5, 8, 50),
    ),
)
```

### Lecture attendue par Onboarding Coach en Consultation

Trois gaps, tous sur Running. Dimensions ciblées : CAPACITY (2 gaps) et TECHNIQUE (1 gap). Confidence sur `(RUNNING, CAPACITY)=0.55`, la plus faible du radar → recalibrer prioritaire. Objectif primary HYBRID avec target chiffré sur semi (1h35) : les gaps running menacent directement la faisabilité de l'objectif.

Décision attendue : produire un `FollowupQuestionSet` (contrat B3) avec 2-3 questions priorisées. Exemple d'output attendu (spec Phase B3) :

```python
[
    FollowupQuestion(
        question="Sur la baseline, j'ai observé que tu as raccourci 3 séances course "
                 "par rapport au prescrit sans blessure. Peux-tu me dire ce qui t'a "
                 "amené à t'arrêter plus tôt que prévu ?",
        targets=["capacity", "volume_tolerance"],
        rationale="Gap significant volume_tolerance discipline running (actual/prescribed=0.72)",
        priority="high",
    ),
    FollowupQuestion(
        question="Pour tes séances tempo, tu visais 4:45/km et elles ont été rapportées "
                 "à RPE 8-9 de manière consistante. Quand tu avais couru 4:30/km "
                 "en référence déclarative, c'était sur quel type de parcours et dans "
                 "quel état de forme ?",
        targets=["capacity", "intensity_tolerance"],
        rationale="Gap significant intensity_tolerance. Confidence CAPACITY=0.55",
        priority="high",
    ),
    FollowupQuestion(
        question="J'ai remarqué des départs plus rapides que l'allure moyenne sur tes "
                 "longues. C'est un pattern que tu reconnais, ou c'est lié à du terrain "
                 "ou d'autres facteurs contextuels ?",
        targets=["technique", "pacing_discipline"],
        rationale="Gap minor pacing_discipline. Confidence TECHNIQUE=0.70",
        priority="medium",
    ),
]
```

Head Coach reformulera ces questions en son propre style et les posera via `head_coach_ask_question`. Les réponses seront appliquées aux sous-profils via `update_profile_deltas` — notamment ré-évaluer `DisciplineExperience[RUNNING].weekly_volume_recent_8w` et la classification `(RUNNING, CAPACITY)`.

---

## Exemple 5 — `NutritionCoachView` en `CHAT_WEEKLY_REPORT`

### Contexte

Même athlète hybride H/33 ans, steady state. 19h00 le 27 avril 2026 (dimanche, fin de semaine d'entraînement). L'utilisateur demande son rapport hebdomadaire. `chat_turn.handle_weekly_report` consulte en parallèle Lifting Coach, Running Coach, Nutrition Coach, Recovery Coach et Energy Coach. Voici ce que Nutrition Coach voit.

Signal à détecter : adherence nutrition 93% (très bonne), mais `user_energy_signal="high"` alors que `objective_ea=38.5` (zone LOW_NORMAL), et sleep debt -8.4h cumulé sur 2 semaines. Pattern à surveiller, à signaler au Head Coach sans escalade vers Energy (EA pas en SUBCLINICAL).

### Construction

```python
NutritionCoachView(
    view_built_at=datetime(2026, 4, 27, 19, 0),
    invocation_trigger=InvocationTrigger.CHAT_WEEKLY_REPORT,

    ident=NutritionCoachIdentView(
        date_of_birth=date(1992, 6, 15),
        biological_sex="male",
        height_cm=178.0,
        weight_kg=74.5,
        ffm_kg=63.1,
        cycle_active=False,
        cycle_phase=None,
        age_years=33,
    ),
    scope=NutritionCoachScopeView(
        nutrition_scope=ScopeLevel.FULL,
        peer_disciplines_active=[Discipline.LIFTING, Discipline.RUNNING],
    ),
    journey=NutritionCoachJourneyView(
        journey_phase=JourneyPhase.STEADY_STATE,
        assessment_mode=False,
    ),
    sub_profiles=NutritionCoachSubProfilesView(
        objective_profile=ObjectiveProfile(
            primary=Objective(
                category=ObjectiveCategory.HYBRID_STRENGTH_ENDURANCE,
                priority=ObjectivePriority.PRIMARY,
                horizon=ObjectiveHorizon.MEDIUM,
                target_date=date(2026, 10, 15),
                target_metric=TargetMetric(
                    metric_name="half_marathon_time",
                    current_value=6000, target_value=5700, unit="sec",
                ),
                free_text_description="Semi sous 1h35 tout en gardant 140kg squat",
                declared_at=datetime(2026, 1, 10),
            ),
            secondary=[],
            trade_offs_acknowledged=[],
            last_revision_at=datetime(2026, 1, 10),
            revision_count=0,
        ),
        injury_history_filtered=NutritionFilteredInjuryHistory(
            relevant_injuries=[],                         # pas d'ACTIVE, pas d'antécédent RED-S
            has_active_injury=False,
            has_history_of_red_s_or_stress_fracture=False,
            has_history_of_disordered_eating_flag=False,
            filtered_at=datetime(2026, 4, 27, 19, 0),
        ),
        practical_constraints_nutrition=NutritionRelevantConstraints(
            meals=MealContext(
                typical_meals_per_day=4,
                dietary_restrictions=["none"],
                dietary_restrictions_notes=None,
                cooking_capability="moderate",
                budget_constraint="moderate",
            ),
            sleep=SleepPattern(
                typical_bedtime="23:00",
                typical_waketime="07:00",
                target_hours_per_night=8.0,
                quality_self_assessment="good",
            ),
            work=WorkContext(
                occupation_physical_demand="sedentary",
                typical_stress_level="moderate",
                travel_frequency="occasional",
            ),
            geographic_context=GeographicContext(
                climate_zone=ClimateZone.COLD_CONTINENTAL,
                altitude_m=150,
                terrain_types_accessible=[TerrainAccessible.ROLLING, TerrainAccessible.HILLY],
                seasonal_variation="marked",
                winter_indoor_substitution_required=True,
            ),
            financial_budget_flag="moderate",
            last_updated_at=datetime(2026, 3, 1),
        ),
    ),
    plans=NutritionCoachPlansView(
        active_plan_blocks=[
            PlanBlock(id="b1", title="Base aerobic + strength accumulation",
                      theme="accumulation", start_date=date(2026, 4, 1),
                      end_date=date(2026, 4, 28), status=BlockStatus.CURRENT,
                      detail_level=BlockDetailLevel.FULL,
                      block_discipline_specs=None,          # masqué pour Nutrition
                      actual_compliance_rate=0.88),
            PlanBlock(id="b2", title="Intensification", theme="intensification",
                      start_date=date(2026, 4, 29), end_date=date(2026, 5, 26),
                      status=BlockStatus.UPCOMING, detail_level=BlockDetailLevel.SUMMARY),
        ],
        active_plan_discipline_components_summary={
            Discipline.LIFTING: DisciplineComponentNutritionSummary(
                discipline=Discipline.LIFTING,
                role_in_plan=DisciplineRoleInPlan.CO_PRIMARY,
                total_volume_arc=[
                    WeeklyVolumePoint(week_number=1, volume=VolumeTarget(value=18, unit=VolumeUnit.TOTAL_WORKING_SETS)),
                    WeeklyVolumePoint(week_number=2, volume=VolumeTarget(value=20, unit=VolumeUnit.TOTAL_WORKING_SETS)),
                    # ...
                ],
            ),
            Discipline.RUNNING: DisciplineComponentNutritionSummary(
                discipline=Discipline.RUNNING,
                role_in_plan=DisciplineRoleInPlan.CO_PRIMARY,
                total_volume_arc=[
                    WeeklyVolumePoint(week_number=1, volume=VolumeTarget(value=45, unit=VolumeUnit.KILOMETERS)),
                    WeeklyVolumePoint(week_number=2, volume=VolumeTarget(value=52, unit=VolumeUnit.KILOMETERS)),
                    # ...
                ],
            ),
        },
        active_plan_trade_offs_relevant=[],               # aucun trade-off composition
        active_plan_status=ActivePlanStatus.ACTIVE,
        active_plan_horizon=PlanHorizon.TWELVE_WEEKS,
        baseline_plan_summary=None,                       # steady state, baseline ancienne
    ),
    derived_readiness=NutritionCoachDerivedReadinessView(
        objective_readiness=ReadinessValue(
            score=72.0,
            contributing_factors={"hrv": 0.30, "sleep": 0.30, "strain": 0.25, "rpe_trend": 0.15},
            computed_at=datetime(2026, 4, 27, 6, 30),
        ),
        user_readiness_signal=UserReadinessSignal(
            score=75.0,
            submitted_at=datetime(2026, 4, 27, 7, 0),
            source="morning_checkin",
        ),
        effective_readiness=EffectiveReadiness(
            score=75.0,
            resolution="user_override_upward",
            user_override_applied=True,
            safeguard_active=None,
        ),
        persistent_override_pattern=PersistentOverridePattern(
            active=False, first_detected_at=None, last_confirmed_at=None,
            consecutive_days_detected=0, divergence_magnitude=None,
            reason=None, set_by=None, reset_by=None, reset_at=None,
        ),
    ),
    derived_ea=NutritionCoachDerivedEAView(
        objective_energy_availability=EnergyAvailabilityValue(
            score=38.5, zone=EAZone.LOW_NORMAL,
            intake_kcal=2850, eee_kcal=425, ffm_kg=63.1,
            computed_at=datetime(2026, 4, 27, 6, 30),
        ),
        user_energy_signal=UserEnergySignal(
            score="high",                                 # divergence : haut vs LOW_NORMAL objective
            numeric_proxy=0.7,
            submitted_at=datetime(2026, 4, 27, 7, 0),
            source="weekly_report",
        ),
        effective_energy_availability=EffectiveEA(
            score=38.5,                                   # override à la hausse autorisé en LOW_NORMAL
            zone=EAZone.LOW_NORMAL,
            resolution="user_override_upward",
            user_override_applied=True,
            safeguard_active=None,
        ),
    ),
    strain_state_aggregate=StrainStateAggregate(
        aggregate=42.0,
        aggregate_history_7d=[38.0, 40.5, 45.0, 48.0, 43.0, 41.0, 42.0],
        last_computed_at=datetime(2026, 4, 27, 6, 0),
        recompute_trigger="daily_decay",
    ),
    allostatic_load_state=AllostaticLoadState(
        current_value=48.0,
        zone=AllostaticLoadZone.NORMAL,
        trend_7d_slope=0.3,
        trend_14d_slope=0.5,
        contributing_factors={
            "strain_aggregate": 0.35, "sleep_debt": 0.10, "hrv_deviation": 0.15,
            "reported_stress": 0.20, "rpe_trend": 0.15, "nutrition_deficit": 0.05,
        },
        history=[...],
        last_computed_at=datetime(2026, 4, 27, 6, 0),
    ),
    nutrition_logs=NutritionLogsWindow(
        window_start=date(2026, 4, 14),                   # 14 jours raw
        window_end=date(2026, 4, 27),
        format="raw",
        daily_points=[
            DailyNutritionPoint(
                date=date(2026, 4, 14),
                calories_kcal=2780, protein_g=180, carbs_g=320, fat_g=85,
                fiber_g=32, meal_count=4,
                target_calories_kcal=2900, target_protein_g=185,
                target_carbs_g=340, target_fat_g=88,
                calories_adherence_ratio=0.959,
                macros_adherence_score=0.92,
                pre_session_meal_logged=True, post_session_meal_logged=True,
                hydration_status="adequate",
            ),
            # ... 13 autres jours
        ],
        summary=NutritionLogsSummary(
            avg_calories_kcal=2820, avg_protein_g=178, avg_carbs_g=325, avg_fat_g=87,
            adherence_rate=0.93, days_with_log_count=13, coverage_rate=0.93,
            last_log_at=datetime(2026, 4, 27, 19, 0),
        ),
    ),
    training_load_history=TrainingLoadHistoryWindow(
        scope="all_active_disciplines",
        window_start=date(2026, 4, 14),
        window_end=date(2026, 4, 27),
        daily_points=[
            LoadHistoryPoint(
                date=date(2026, 4, 14), discipline=Discipline.LIFTING,
                total_volume=VolumeTarget(value=22, unit=VolumeUnit.TOTAL_WORKING_SETS),
                session_count=1, avg_rpe=7.5,
                aggregated_strain_contribution=8.5, estimated_eee_kcal=380,
            ),
            LoadHistoryPoint(
                date=date(2026, 4, 15), discipline=Discipline.RUNNING,
                total_volume=VolumeTarget(value=10.5, unit=VolumeUnit.KILOMETERS),
                session_count=1, avg_rpe=6.0,
                aggregated_strain_contribution=6.0, estimated_eee_kcal=620,
            ),
            # ... 14 jours × disciplines actives
        ],
        total_volume=None,
        avg_weekly_strain_contribution=38.5,
        avg_daily_eee_kcal=485,
        total_session_count=8,
        coverage_rate=1.0,
    ),
    physio_logs=PhysioLogsWindow(
        window_start=date(2026, 4, 14),                   # 14 jours summary
        window_end=date(2026, 4, 27),
        format="summary_only",
        daily_points=None,
        summary=PhysioLogsSummary(
            hrv_trend_slope_per_day=-0.2,
            hrv_deviations_count=1,
            hrv_last_value=52.3,
            sleep_avg_hours=7.4,
            sleep_debt_cumulative_hours=-8.4,             # 0.6h/nuit sous target 8h
            sleep_last_quality=78.0,
            rhr_trend_slope_per_day=0.05,
            weight_trend_slope_per_week_kg=-0.05,
            last_log_at=datetime(2026, 4, 27, 7, 15),
            coverage_rate=0.86,
        ),
    ),
    caution_elevated=False,                               # pas d'injury ni antécédent RED-S
)
```

### Lecture attendue par Nutrition Coach

`effective_ea.zone=LOW_NORMAL` avec adherence 93% — paradoxe : l'athlète mange ce qu'on lui prescrit, mais les targets sont peut-être trop bas vs la dépense. `user_energy_signal="high"` → override upward sur EA : le user s'auto-signale en forme. Sleep debt -8.4h sur 14j, HRV slope légèrement négatif.

`caution_elevated=False` : pas d'antécédent RED-S ni troubles alimentaires, posture plus sereine permise. Mais convergence "EA basse + signal user déconnecté + sleep debt" mérite d'être surfacée sans catastrophiser.

Décision attendue : `NutritionVerdict` (contrat B3) avec :
- `status="mild_adjustment"` (pas "concern" car pattern pas encore installé)
- `daily_targets` : légère hausse calorique proposée (+100-150 kcal) pour ramener EA vers OPTIMAL, protéine maintenue
- `adjustment_suggestion="Augmenter le dîner de 100-150 kcal pour 2 semaines, revoir si sleep ou HRV continuent à se dégrader"`
- `flag_for_head_coach="EA en zone LOW_NORMAL avec sleep debt modéré ; adherence excellente mais targets possiblement sous-estimés vs charge actuelle. Pas d'escalade Energy Coach encore (pattern pas en SUBCLINICAL)."`
- `pass_to_energy_coach=False`

Si la semaine suivante le pattern persiste (EA toujours LOW_NORMAL + user toujours "high" + sleep débit qui creuse), Nutrition Coach passera à `pass_to_energy_coach=True` pour escalader.

---

## Exemple 6 — `RecoveryCoachView` en `RECOVERY_ASSESS_SITUATION` (takeover actif)

### Contexte

Même athlète hybride H/33 ans. 10h15 le 23 avril 2026. L'utilisateur a rapporté une douleur au genou droit la veille via `handle_injury_report`. Le node `activate_clinical_frame` a déjà exécuté : `recovery_takeover_active=True`, `active_plan.status=SUSPENDED`. Le Recovery Coach est maintenant invoqué en `assess_situation` pour poser des questions diagnostiques. Cadre UX distinct côté frontend.

Convergence de signaux alarmante : tendinopathie rotulienne suspectée, HRV en chute sur 3 jours, sleep debt, allostatic load ELEVATED, antécédent chronique même région.

### Construction

```python
RecoveryCoachView(
    view_built_at=datetime(2026, 4, 23, 10, 15),
    invocation_trigger=InvocationTrigger.RECOVERY_ASSESS_SITUATION,
    is_in_takeover=True,

    ident=RecoveryCoachIdentView(
        date_of_birth=date(1992, 6, 15),
        biological_sex="male",
        height_cm=178.0, weight_kg=74.5, ffm_kg=63.1,
        cycle_active=False,
        cycle_phase=None, cycle_day=None, cycle_length_days=None,
        age_years=33,
    ),
    scope=RecoveryCoachScopeView(
        coaching_scope={
            Domain.LIFTING: ScopeLevel.FULL,
            Domain.RUNNING: ScopeLevel.FULL,
            Domain.SWIMMING: ScopeLevel.DISABLED,
            Domain.BIKING: ScopeLevel.TRACKING,
            Domain.NUTRITION: ScopeLevel.FULL,
            Domain.RECOVERY: ScopeLevel.FULL,
        },
        peer_disciplines_active=[Discipline.LIFTING, Discipline.RUNNING],
    ),
    journey=RecoveryCoachJourneyView(
        journey_phase=JourneyPhase.STEADY_STATE,
        recovery_takeover_active=True,
        onboarding_reentry_active=False,
        assessment_mode=False,
    ),
    sub_profiles=RecoveryCoachSubProfilesView(
        experience_profile=ExperienceProfile(...),        # complet
        objective_profile=ObjectiveProfile(
            primary=Objective(
                category=ObjectiveCategory.HYBRID_STRENGTH_ENDURANCE,
                target_date=date(2026, 10, 15),           # semi dans 6 mois
                # ...
            ),
            # ...
        ),
        injury_history=InjuryHistory(                      # COMPLET, non filtré
            injuries=[
                # ACTIVE : la tendinopathie que l'user vient de rapporter
                InjuryRecord(
                    injury_id="inj-active-001",
                    region=BodyRegion.KNEE,
                    side=InjurySide.RIGHT,
                    specific_structure="rotulian_tendon",
                    status=InjuryStatus.ACTIVE,
                    severity=InjurySeverity.MODERATE,
                    onset_date=date(2026, 4, 22),
                    mechanism="Douleur progressive sur 5 jours, pas de trauma",
                    diagnosis="Tendinopathie rotulienne suspectée",
                    diagnosed_by_professional=False,
                    contraindications=[],
                    triggered_recovery_takeover=True,
                    linked_recovery_thread_id="abc-123:recovery_takeover:7a9b...",
                    declared_by="recovery_coach",
                    declared_at=datetime(2026, 4, 23, 10, 0),
                    last_updated_at=datetime(2026, 4, 23, 10, 15),
                ),
                # CHRONIC_MANAGED : antécédent même région
                InjuryRecord(
                    injury_id="inj-chronic-001",
                    region=BodyRegion.KNEE,
                    side=InjurySide.RIGHT,
                    status=InjuryStatus.CHRONIC_MANAGED,
                    severity=InjurySeverity.MILD,
                    onset_date=date(2023, 6, 15),
                    diagnosis="Tendinite rotulienne récurrente",
                    contraindications=[
                        Contraindication(
                            type=ContraindicationType.REDUCE_VOLUME,
                            target="back_squat",
                            notes="Volume lourd > 20 sets/sem augmente douleurs",
                        ),
                    ],
                    declared_by="onboarding_coach",
                    declared_at=datetime(2026, 1, 10),
                    last_updated_at=datetime(2026, 1, 10),
                ),
                # HISTORICAL : entorse cheville 4 ans avant (inclus, Recovery voit tout)
                InjuryRecord(
                    injury_id="inj-historical-001",
                    region=BodyRegion.ANKLE, side=InjurySide.LEFT,
                    status=InjuryStatus.HISTORICAL,
                    severity=InjurySeverity.MODERATE,
                    onset_date=date(2022, 8, 10), resolved_date=date(2022, 10, 1),
                    diagnosis="Entorse grade 2",
                    declared_by="onboarding_coach",
                    declared_at=datetime(2026, 1, 10),
                    last_updated_at=datetime(2026, 1, 10),
                ),
            ],
            has_active_injury=True,
            has_chronic_managed=True,
            last_updated_at=datetime(2026, 4, 23, 10, 15),
        ),
        practical_constraints=PracticalConstraints(
            sleep=SleepPattern(
                typical_bedtime="23:00", typical_waketime="07:00",
                target_hours_per_night=8.0, quality_self_assessment="good",
            ),
            work=WorkContext(
                occupation_physical_demand="sedentary",
                typical_stress_level="moderate", travel_frequency="occasional",
            ),
            # ...
        ),
    ),
    classification=RecoveryCoachClassificationView(
        classification={
            Discipline.LIFTING: DimensionClassification(
                capacity=ClassificationLevel.INTERMEDIATE,
                technique=ClassificationLevel.ADVANCED,
                history=ClassificationLevel.ADVANCED,
            ),
            Discipline.RUNNING: DimensionClassification(
                capacity=ClassificationLevel.INTERMEDIATE,
                technique=ClassificationLevel.INTERMEDIATE,
                history=ClassificationLevel.BEGINNER_ADVANCED,
            ),
        },
        confidence_levels={
            (Discipline.LIFTING, ClassificationDimension.CAPACITY): 0.75,
            (Discipline.LIFTING, ClassificationDimension.TECHNIQUE): 0.90,
            (Discipline.LIFTING, ClassificationDimension.HISTORY): 0.95,
            (Discipline.RUNNING, ClassificationDimension.CAPACITY): 0.55,
            (Discipline.RUNNING, ClassificationDimension.TECHNIQUE): 0.70,
            (Discipline.RUNNING, ClassificationDimension.HISTORY): 0.60,
        },
    ),
    plans=RecoveryCoachPlansView(
        active_plan=ActivePlan(
            plan_id="plan-042",
            status=ActivePlanStatus.SUSPENDED,             # suspendu par activate_clinical_frame
            suspended_at=datetime(2026, 4, 23, 10, 0),
            suspended_reason="Tendinopathie rotulienne rapportée",
            suspension_triggered_by="recovery_coach",
            last_modification_at=datetime(2026, 4, 23, 10, 0),
            last_modification_type="suspension",
            modification_count=1,
            # ... blocs, composants
        ),
        baseline_plan=None,
    ),
    strain_state=StrainState(                              # COMPLET avec origine
        by_group={
            MuscleGroup.QUADS: MuscleGroupStrain(
                current_value=48.0, peak_24h=62.0, ewma_tau_days=3.0,
                last_contribution_at=datetime(2026, 4, 22, 19, 0),  # visible pour Recovery
            ),
            MuscleGroup.HAMSTRINGS: MuscleGroupStrain(
                current_value=35.0, peak_24h=42.0, ewma_tau_days=3.0,
                last_contribution_at=datetime(2026, 4, 21, 19, 0),
            ),
            # ... 16 autres groupes
        },
        aggregate=38.5,
        history=[...],                                    # 21 points
        last_computed_at=datetime(2026, 4, 23, 6, 0),
        recompute_trigger="daily_decay",
    ),
    derived_readiness=RecoveryCoachDerivedReadinessView(
        objective_readiness=ReadinessValue(
            score=58.0,
            contributing_factors={"hrv": 0.30, "sleep": 0.30, "strain": 0.25, "rpe_trend": 0.15},
            computed_at=datetime(2026, 4, 23, 6, 30),
        ),
        user_readiness_signal=UserReadinessSignal(
            score=45.0, submitted_at=datetime(2026, 4, 23, 7, 0),
            source="morning_checkin",
        ),
        effective_readiness=EffectiveReadiness(
            score=58.0,                                    # takeover prime, override user neutralisé
            resolution="takeover_neutralized",
            user_override_applied=False,
            safeguard_active="recovery_takeover",
        ),
        persistent_override_pattern=PersistentOverridePattern(
            active=False, first_detected_at=None, last_confirmed_at=None,
            consecutive_days_detected=0, divergence_magnitude=None,
            reason=None, set_by=None, reset_by=None, reset_at=None,
        ),
    ),
    derived_ea=RecoveryCoachDerivedEAView(
        objective_energy_availability=EnergyAvailabilityValue(
            score=38.5, zone=EAZone.LOW_NORMAL,
            intake_kcal=2820, eee_kcal=385, ffm_kg=63.1,
            computed_at=datetime(2026, 4, 23, 6, 30),
        ),
        user_energy_signal=UserEnergySignal(
            score="neutral", numeric_proxy=0.0,
            submitted_at=datetime(2026, 4, 23, 7, 0), source="daily_checkin",
        ),
        effective_energy_availability=EffectiveEA(
            score=38.5, zone=EAZone.LOW_NORMAL,
            resolution="takeover_neutralized",
            user_override_applied=False,
            safeguard_active="recovery_takeover",
        ),
    ),
    allostatic_load_state=AllostaticLoadState(
        current_value=68.0,
        zone=AllostaticLoadZone.ELEVATED,                  # signal convergent
        trend_7d_slope=2.1,
        trend_14d_slope=1.5,
        contributing_factors={
            "strain_aggregate": 0.30, "sleep_debt": 0.15, "hrv_deviation": 0.25,
            "reported_stress": 0.15, "rpe_trend": 0.10, "nutrition_deficit": 0.05,
        },
        history=[...],
        last_computed_at=datetime(2026, 4, 23, 6, 0),
    ),
    technical=RecoveryCoachTechnicalView(
        active_recovery_thread_id="abc-123:recovery_takeover:7a9b...",
        connector_status={
            ConnectorName.STRAVA: ConnectorStatus(
                active=True, last_sync_at=datetime(2026, 4, 23, 5, 30),
            ),
            ConnectorName.APPLE_HEALTH: ConnectorStatus(
                active=True, last_sync_at=datetime(2026, 4, 23, 7, 0),
            ),
        },
        validation_warnings=[],
    ),
    convo=RecoveryCoachConvoView(
        last_classified_intent=ClassifiedIntent.INJURY_REPORT,
        last_message_at=datetime(2026, 4, 23, 10, 12),
        messages=MessagesWindow(
            scope="current_thread",
            thread_id="abc-123:recovery_takeover:7a9b...",
            window_start=datetime(2026, 4, 23, 10, 0),
            window_end=datetime(2026, 4, 23, 10, 15),
            messages=[
                MessageLite(
                    message_id="msg-rec-1",
                    thread_id="abc-123:recovery_takeover:7a9b...",
                    timestamp=datetime(2026, 4, 23, 10, 0),
                    author="recovery_coach",
                    content="Je prends le relais pour évaluer ce genou. "
                            "Quelques questions pour situer précisément.",
                ),
                MessageLite(
                    message_id="msg-rec-2",
                    thread_id="abc-123:recovery_takeover:7a9b...",
                    timestamp=datetime(2026, 4, 23, 10, 3),
                    author="recovery_coach",
                    content="Douleur localisée où exactement ? Pointe, sous la rotule, "
                            "ou derrière ?",
                ),
                MessageLite(
                    message_id="msg-rec-3",
                    thread_id="abc-123:recovery_takeover:7a9b...",
                    timestamp=datetime(2026, 4, 23, 10, 5),
                    author="user",
                    content="Sous la rotule, côté médial. Ça chauffe après les squats lourds.",
                ),
                # ... 4 autres messages
            ],
            truncated=False,
            total_count_in_window=7,
        ),
    ),
    training_logs={
        Discipline.LIFTING: TrainingLogsRawWindow(
            discipline=Discipline.LIFTING,
            window_start=date(2026, 3, 26),               # 28 jours
            window_end=date(2026, 4, 22),
            sessions=[
                SessionLogLite(
                    log_id="sess-l-12",
                    discipline=Discipline.LIFTING,
                    session_type="lower_body_strength",
                    session_date=date(2026, 4, 22),
                    duration_minutes=75,
                    volume_realized=VolumeTarget(value=24, unit=VolumeUnit.TOTAL_WORKING_SETS),
                    intensity_realized={"avg_pct_1rm": 0.82},
                    rpe_reported=8.5,
                    prescribed_session_id="presc-l-12",
                    compliance_status="on_plan",
                    strain_contribution_total=12.5,
                    strain_contribution_by_group={
                        MuscleGroup.QUADS: 8.0, MuscleGroup.HAMSTRINGS: 3.5, MuscleGroup.GLUTES: 4.0,
                    },
                    notes="Douleur genou droit en fin de séance sur back squat",
                    exercise_details=None,                 # hydrate_exercise_details=False pour Recovery
                    interval_details=None,
                ),
                # ... 11 autres séances lifting sur 28j
            ],
            total_sessions_count=11,
            total_volume_realized=VolumeTarget(value=265, unit=VolumeUnit.TOTAL_WORKING_SETS),
            avg_rpe=7.9,
            compliance_rate=0.92,
            last_session_at=datetime(2026, 4, 22, 19, 0),
            coverage_rate=0.97,
        ),
        Discipline.RUNNING: TrainingLogsRawWindow(
            discipline=Discipline.RUNNING,
            window_start=date(2026, 3, 26),
            window_end=date(2026, 4, 22),
            sessions=[
                SessionLogLite(
                    log_id="sess-r-15",
                    discipline=Discipline.RUNNING,
                    session_type="tempo",
                    session_date=date(2026, 4, 20),
                    duration_minutes=45,
                    volume_realized=VolumeTarget(value=10.5, unit=VolumeUnit.KILOMETERS),
                    intensity_realized={"zone_3_ratio": 0.75, "avg_hr": 165},
                    rpe_reported=8.0,
                    prescribed_session_id="presc-r-15",
                    compliance_status="on_plan",
                    strain_contribution_total=8.5,
                    strain_contribution_by_group={
                        MuscleGroup.QUADS: 4.0, MuscleGroup.CALVES: 2.5,
                    },
                    exercise_details=None,
                    interval_details=None,
                ),
                # ... 11 autres séances
            ],
            total_sessions_count=12,
            total_volume_realized=VolumeTarget(value=168, unit=VolumeUnit.KILOMETERS),
            avg_rpe=6.8,
            compliance_rate=0.88,
            last_session_at=datetime(2026, 4, 20, 18, 30),
            coverage_rate=0.93,
        ),
        # Pas de BIKING dans Recovery : pas de log récent sur discipline TRACKING
    },
    physio_logs=PhysioLogsWindow(
        window_start=date(2026, 3, 24),                   # 30 jours RAW
        window_end=date(2026, 4, 22),
        format="raw",                                      # seul agent avec raw physio
        daily_points=[
            DailyPhysioPoint(
                date=date(2026, 4, 20),
                hrv_rmssd_ms=48.0, hrv_deviation_z_score=-0.8,
                sleep_duration_hours=7.8, sleep_quality_score=82,
                resting_heart_rate_bpm=55, weight_kg=74.5,
                subjective_stress="moderate", subjective_energy="neutral",
                morning_checkin_submitted=True,
            ),
            DailyPhysioPoint(
                date=date(2026, 4, 21),
                hrv_rmssd_ms=42.0, hrv_deviation_z_score=-1.3,   # baisse
                sleep_duration_hours=6.5, sleep_quality_score=68,
                resting_heart_rate_bpm=58, weight_kg=74.6,
                subjective_stress="high", subjective_energy="low",
                morning_checkin_submitted=True,
            ),
            DailyPhysioPoint(
                date=date(2026, 4, 22),
                hrv_rmssd_ms=38.5, hrv_deviation_z_score=-1.7,   # plus bas
                sleep_duration_hours=6.8, sleep_quality_score=72,
                resting_heart_rate_bpm=60, weight_kg=74.5,
                subjective_stress="high", subjective_energy="low",
                morning_checkin_submitted=True,
            ),
            # ... 27 autres jours
        ],
        summary=PhysioLogsSummary(
            hrv_trend_slope_per_day=-0.3,
            hrv_deviations_count=5,                       # dont les 3 derniers
            hrv_last_value=38.5,
            sleep_avg_hours=7.1,
            sleep_debt_cumulative_hours=-27.0,
            sleep_last_quality=72.0,
            rhr_trend_slope_per_day=0.15,
            weight_trend_slope_per_week_kg=-0.05,
            last_log_at=datetime(2026, 4, 23, 7, 15),
            coverage_rate=0.97,
        ),
    ),
    nutrition_logs=NutritionLogsWindow(
        window_start=date(2026, 4, 9),                    # 14 jours summary
        window_end=date(2026, 4, 22),
        format="summary_only",
        daily_points=None,
        summary=NutritionLogsSummary(
            avg_calories_kcal=2820, avg_protein_g=178, avg_carbs_g=325, avg_fat_g=87,
            adherence_rate=0.93, days_with_log_count=13, coverage_rate=0.93,
            last_log_at=datetime(2026, 4, 22, 20, 30),
        ),
    ),
    monitoring_event_payload=None,                         # trigger RECOVERY_*, pas MONITORING_*
)
```

### Lecture attendue par Recovery Coach

Situation clinique claire : active injury déclarée (tendinopathie rotulienne droite), antécédent chronique identique même région (CHRONIC_MANAGED), contre-indication préexistante sur back_squat volume > 20 sets/sem. Contexte training : dernière séance lifting lundi avec RPE 8.5 et 24 sets (au-dessus du seuil chronique), notes explicites "Douleur genou droit en fin de séance sur back squat".

Signaux physio convergents : HRV en chute Z -0.8 → -1.3 → -1.7 sur 3 jours, sleep debt -27h cumulé sur 30j, allostatic load 68 (ELEVATED). Pattern de surcharge probable.

L'athlète est en pleine préparation d'un semi dans 6 mois — enjeu de temps modéré, pas d'urgence compétitive immédiate qui justifierait de prendre des risques.

`effective_readiness.resolution="takeover_neutralized"` : le takeover est actif, l'override user est neutralisé, tout ce qui compte est le signal objectif.

Décision attendue : poser 2-3 questions diagnostiques précises (localisation, déclencheur, amplitude actuelle sans douleur, historique d'aggravation sur les 5 derniers jours). Puis passer au node `propose_protocol` avec protocole conservateur (7-10 jours repos lifting jambes + natation ou vélo zone 2 pour maintenir aérobie + exercices isométriques rééducation selon protocoles Phase C). Messages conversationnels directs (pas de contrat B3 structuré en takeover). Si user confirme protocole, `set_suspension_parameters` puis `monitor_recovery_loop`.

---

## Exemple 7 — `EnergyCoachView` en `ESCALATION_NUTRITION_TO_ENERGY`

### Contexte

**Nouvel athlète** : femme, 32 ans, 168cm/58.5kg/FFM 47kg, cycle actif (jour 24/28, phase lutéale tardive). Steady state. Objectif primaire `FAT_LOSS` avec target -4.5kg sur 6 mois, STRENGTH_MAX en secondary avec trade-off COMPOSITION_COMPROMISED acknowledgé. Bloc en cours "Cut + strength maintenance" (2026-03-15 → 2026-06-07).

11h00 le 11 mai 2026. Nutrition Coach a détecté en weekly_report que l'EA est en zone LOW_NORMAL depuis 8 semaines consécutives, l'user signale "energy=high" quotidiennement malgré HRV en baisse lente et sleep debt qui s'accumule. Nutrition émet `pass_to_energy_coach=True` dans son `NutritionVerdict`. Le Coordinator invoque Energy Coach avec `EscalationContext`.

### Construction

```python
EnergyCoachView(
    view_built_at=datetime(2026, 5, 11, 9, 0),
    invocation_trigger=InvocationTrigger.ESCALATION_NUTRITION_TO_ENERGY,

    ident=EnergyCoachIdentView(
        date_of_birth=date(1994, 3, 20),
        biological_sex="female",
        height_cm=168.0,
        weight_kg=58.5,
        ffm_kg=47.0,
        cycle_active=True,
        cycle_phase=CyclePhase.LUTEAL_LATE,
        cycle_day=24,
        cycle_length_days=28,
        age_years=32,
    ),
    scope=EnergyCoachScopeView(
        coaching_scope={
            Domain.LIFTING: ScopeLevel.FULL,
            Domain.RUNNING: ScopeLevel.FULL,
            Domain.SWIMMING: ScopeLevel.DISABLED,
            Domain.BIKING: ScopeLevel.DISABLED,
            Domain.NUTRITION: ScopeLevel.FULL,
            Domain.RECOVERY: ScopeLevel.FULL,
        },
        peer_disciplines_active=[Discipline.LIFTING, Discipline.RUNNING],
        disciplines_tracked=[],
        nutrition_scope=ScopeLevel.FULL,
    ),
    journey=EnergyCoachJourneyView(
        journey_phase=JourneyPhase.STEADY_STATE,
        assessment_mode=False,
    ),
    sub_profiles=EnergyCoachSubProfilesView(
        objective_profile=ObjectiveProfile(
            primary=Objective(
                category=ObjectiveCategory.FAT_LOSS,       # signal : objectif calorique restrictif
                priority=ObjectivePriority.PRIMARY,
                horizon=ObjectiveHorizon.MEDIUM,
                target_date=date(2026, 8, 1),
                target_metric=TargetMetric(
                    metric_name="body_weight",
                    current_value=58.5, target_value=54.0, unit="kg",
                ),
                declared_at=datetime(2026, 2, 1),
            ),
            secondary=[
                Objective(
                    category=ObjectiveCategory.STRENGTH_MAX,
                    priority=ObjectivePriority.SECONDARY,
                    horizon=ObjectiveHorizon.OPEN_ENDED,
                    declared_at=datetime(2026, 2, 1),
                ),
            ],
            trade_offs_acknowledged=[
                TradeOffDeclaration(
                    sacrificed_objective_category=ObjectiveCategory.STRENGTH_MAX,
                    protected_objective_category=ObjectiveCategory.FAT_LOSS,
                    user_acknowledged_at=datetime(2026, 2, 1),
                ),
            ],
            last_revision_at=datetime(2026, 2, 1),
            revision_count=0,
        ),
        injury_history_filtered=NutritionFilteredInjuryHistory(
            relevant_injuries=[],
            has_active_injury=False,
            has_history_of_red_s_or_stress_fracture=False,
            has_history_of_disordered_eating_flag=False,
            filtered_at=datetime(2026, 5, 11, 9, 0),
        ),
        practical_constraints_energy=EnergyRelevantConstraints(
            meals=MealContext(
                typical_meals_per_day=3, dietary_restrictions=["none"],
                cooking_capability="moderate", budget_constraint="moderate",
            ),
            sleep=SleepPattern(
                typical_bedtime="23:30", typical_waketime="06:30",
                target_hours_per_night=7.5, quality_self_assessment="fair",
            ),
            work=WorkContext(
                occupation_physical_demand="sedentary",
                typical_stress_level="high", travel_frequency="occasional",
            ),
            geographic_context=GeographicContext(
                climate_zone=ClimateZone.COLD_CONTINENTAL,
                altitude_m=150,
                terrain_types_accessible=[TerrainAccessible.ROLLING],
                seasonal_variation="marked",
                winter_indoor_substitution_required=True,
            ),
            last_updated_at=datetime(2026, 2, 1),
        ),
    ),
    plans=EnergyCoachPlansView(
        active_plan_blocks=[
            PlanBlock(id="b1", title="Cut + strength maintenance",
                      theme="fat_loss_protective",
                      start_date=date(2026, 3, 15), end_date=date(2026, 6, 7),
                      status=BlockStatus.CURRENT, detail_level=BlockDetailLevel.FULL,
                      actual_compliance_rate=0.91),
            PlanBlock(id="b2", title="Refeed", theme="diet_break",
                      start_date=date(2026, 6, 8), end_date=date(2026, 6, 21),
                      status=BlockStatus.UPCOMING, detail_level=BlockDetailLevel.SUMMARY),
        ],
        active_plan_discipline_components_projection={
            Discipline.LIFTING: DisciplineComponentEnergyProjection(
                discipline=Discipline.LIFTING,
                role_in_plan=DisciplineRoleInPlan.PRIMARY,
                total_volume_arc=[
                    WeeklyVolumePointWithEEE(
                        week_number=1,
                        volume=VolumeTarget(value=16, unit=VolumeUnit.TOTAL_WORKING_SETS),
                        estimated_weekly_eee_kcal=1200,
                    ),
                    # ... 11 autres semaines
                ],
                projected_total_eee_kcal_over_plan=15800,
                deprioritized_vs_ideal=False,
            ),
            Discipline.RUNNING: DisciplineComponentEnergyProjection(
                discipline=Discipline.RUNNING,
                role_in_plan=DisciplineRoleInPlan.SECONDARY,
                total_volume_arc=[
                    WeeklyVolumePointWithEEE(
                        week_number=1,
                        volume=VolumeTarget(value=30, unit=VolumeUnit.KILOMETERS),
                        estimated_weekly_eee_kcal=1800,
                    ),
                    # ...
                ],
                projected_total_eee_kcal_over_plan=22500,
                deprioritized_vs_ideal=False,
            ),
        },
        active_plan_trade_offs_relevant=[
            TradeOff(
                category=TradeOffCategory.COMPOSITION_COMPROMISED,
                sacrificed_element="strength_progression",
                protected_element="fat_loss_rate",
                rationale="Déficit calorique modéré prioritaire, gains force ralentis",
                magnitude="moderate",
                disclosed_at=datetime(2026, 3, 14),
                disclosed_in_plan_id="plan-015",
                acknowledged_by_user=True,
                acknowledged_at=datetime(2026, 3, 14),
            ),
        ],
        active_plan_status=ActivePlanStatus.ACTIVE,
        active_plan_horizon=PlanHorizon.TWELVE_WEEKS,
        active_plan_start_date=date(2026, 3, 15),
        active_plan_end_date=date(2026, 6, 7),
        baseline_plan_summary=None,
    ),
    strain=EnergyCoachDerivedStrainView(
        current_aggregate=42.0,
        weekly_aggregates=[
            WeeklyStrainPoint(week_start=date(2026, 3, 17), week_end=date(2026, 3, 23),
                              avg_aggregate=45.2, peak_aggregate=58.0, days_with_data=7),
            WeeklyStrainPoint(week_start=date(2026, 3, 24), week_end=date(2026, 3, 30),
                              avg_aggregate=43.8, peak_aggregate=55.0, days_with_data=7),
            # ... 8 semaines sur 60j
        ],
        last_computed_at=datetime(2026, 5, 11, 6, 0),
        recompute_trigger="daily_decay",
    ),
    derived_readiness=EnergyCoachDerivedReadinessView(
        objective_readiness=ReadinessValue(
            score=64.0,
            contributing_factors={"hrv": 0.30, "sleep": 0.30, "strain": 0.25, "rpe_trend": 0.15},
            computed_at=datetime(2026, 5, 11, 6, 30),
        ),
        user_readiness_signal=UserReadinessSignal(
            score=78.0,                                   # divergence forte +14 points
            submitted_at=datetime(2026, 5, 11, 7, 0),
            source="morning_checkin",
        ),
        effective_readiness=EffectiveReadiness(
            score=78.0,
            resolution="user_override_upward",
            user_override_applied=True,
            safeguard_active=None,
        ),
        persistent_override_pattern=PersistentOverridePattern(
            active=False,                                  # pas encore flag, mais divergence émerge
            first_detected_at=None,
            last_confirmed_at=None,
            consecutive_days_detected=3,                   # Recovery surveille, seuil 5j
            divergence_magnitude=12.0,
            reason=None,
            set_by=None,
            reset_by=None,
            reset_at=None,
        ),
    ),
    derived_ea=EnergyCoachDerivedEAView(
        objective_energy_availability=EnergyAvailabilityValue(
            score=32.5, zone=EAZone.LOW_NORMAL,
            intake_kcal=1950, eee_kcal=425, ffm_kg=47.0,
            computed_at=datetime(2026, 5, 11, 6, 30),
        ),
        user_energy_signal=UserEnergySignal(
            score="high",                                  # divergence déni énergétique
            numeric_proxy=0.7,
            submitted_at=datetime(2026, 5, 11, 7, 0),
            source="daily_checkin",
        ),
        effective_energy_availability=EffectiveEA(
            score=32.5, zone=EAZone.LOW_NORMAL,
            resolution="user_override_upward",             # autorisé en LOW_NORMAL
            user_override_applied=True,
            safeguard_active=None,
        ),
        ea_zone_trajectory=[
            EAZoneWeekPoint(
                week_start=date(2026, 3, 15), week_end=date(2026, 3, 21),
                avg_ea_kcal_per_kg_ffm=42.0,
                dominant_zone=EAZone.LOW_NORMAL,
                days_per_zone={EAZone.OPTIMAL: 1, EAZone.LOW_NORMAL: 6, EAZone.SUBCLINICAL: 0},
                days_with_complete_data=7,
            ),
            EAZoneWeekPoint(
                week_start=date(2026, 3, 22), week_end=date(2026, 3, 28),
                avg_ea_kcal_per_kg_ffm=41.5,
                dominant_zone=EAZone.LOW_NORMAL,
                days_per_zone={EAZone.OPTIMAL: 0, EAZone.LOW_NORMAL: 7, EAZone.SUBCLINICAL: 0},
                days_with_complete_data=7,
            ),
            # ... 6 autres semaines, trajectoire dégradante
            EAZoneWeekPoint(
                week_start=date(2026, 5, 3), week_end=date(2026, 5, 9),
                avg_ea_kcal_per_kg_ffm=33.0,
                dominant_zone=EAZone.LOW_NORMAL,
                days_per_zone={EAZone.OPTIMAL: 0, EAZone.LOW_NORMAL: 5, EAZone.SUBCLINICAL: 2},
                days_with_complete_data=7,
            ),
        ],
    ),
    allostatic_load_state=AllostaticLoadState(
        current_value=58.0,
        zone=AllostaticLoadZone.ELEVATED,
        trend_7d_slope=1.2,
        trend_14d_slope=0.8,
        contributing_factors={
            "strain_aggregate": 0.25, "sleep_debt": 0.15, "hrv_deviation": 0.15,
            "reported_stress": 0.20, "rpe_trend": 0.10,
            "nutrition_deficit": 0.15,                    # contributeur croissant
        },
        history=[...],
        last_computed_at=datetime(2026, 5, 11, 6, 0),
    ),
    nutrition_logs=NutritionLogsWindow(
        window_start=date(2026, 4, 13),                   # 28 jours raw
        window_end=date(2026, 5, 10),
        format="raw",
        daily_points=[...],
        summary=NutritionLogsSummary(
            avg_calories_kcal=1960, avg_protein_g=125, avg_carbs_g=195, avg_fat_g=62,
            adherence_rate=0.94,                          # paradoxe : adhérent mais déficit structurel
            days_with_log_count=27, coverage_rate=0.96,
            last_log_at=datetime(2026, 5, 10, 20, 30),
        ),
    ),
    training_load_history=TrainingLoadHistoryWindow(
        scope="all_active_disciplines",
        window_start=date(2026, 3, 13),                   # 60 jours load_history
        window_end=date(2026, 5, 10),
        daily_points=[...],                               # 60 jours × disciplines actives
        total_volume=None,
        avg_weekly_strain_contribution=42.0,
        avg_daily_eee_kcal=425,
        total_session_count=48,
        coverage_rate=0.97,
    ),
    physio_logs=PhysioLogsWindow(
        window_start=date(2026, 4, 11),                   # 30 jours summary
        window_end=date(2026, 5, 10),
        format="summary_only",
        daily_points=None,
        summary=PhysioLogsSummary(
            hrv_trend_slope_per_day=-0.15,                # baisse lente
            hrv_deviations_count=3,
            hrv_last_value=45.2,
            sleep_avg_hours=7.0,
            sleep_debt_cumulative_hours=-15.0,
            sleep_last_quality=68.0,
            rhr_trend_slope_per_day=0.1,
            weight_trend_slope_per_week_kg=-0.35,         # perte cohérente avec objectif
            last_log_at=datetime(2026, 5, 11, 6, 45),
            coverage_rate=0.93,
        ),
    ),
    monitoring_event_payload=None,
    escalation_context=EscalationContext(
        source_agent="nutrition_coach",
        escalated_at=datetime(2026, 5, 11, 8, 55),
        nutrition_verdict_summary=(
            "EA en zone LOW_NORMAL sur 8 semaines consécutives. User signale énergie "
            "élevée quotidiennement malgré baisse HRV et sommeil dégradé. Pattern "
            "évocateur de déni énergétique émergent. Objectif FAT_LOSS actif mais "
            "trade-off COMPOSITION_COMPROMISED acknowledgé."
        ),
        detected_patterns=[
            "ea_low_normal_8_weeks",
            "declared_energy_high_despite_low_ea",
            "hrv_downward_trend_3w",
            "fat_loss_objective_active_with_risk_signals",
        ],
        preliminary_flag="escalate_to_energy_coach",
        related_nutrition_log_ids=["nut-log-451", "nut-log-458", "nut-log-465"],
    ),
)
```

### Lecture attendue par Energy Coach

Pattern RED-S **émergent mais pas clinique**. EA LOW_NORMAL sur 8 semaines consécutives (`ea_zone_trajectory` montre la trajectoire : 42.0 → 41.5 → ... → 33.0 la dernière semaine avec 2 jours SUBCLINICAL). HRV en baisse lente, sleep debt -15h sur 30j, poids qui descend conformément à l'objectif FAT_LOSS (-0.35 kg/semaine, dans la norme). Allostatic load 58 (ELEVATED), contributeur `nutrition_deficit=0.15` en croissance.

Phase lutéale tardive actuelle (`cycle_phase=LUTEAL_LATE`, jour 24/28) : besoins métaboliques +5-10%, ce qui aggrave le déficit relatif. `persistent_override_pattern.active=False` mais `consecutive_days_detected=3, divergence_magnitude=12.0` — Recovery surveille déjà.

Signal clé pour Energy : l'athlète ne se rend pas compte de son déficit, elle signale "energy=high" systématiquement alors que les métriques objectives convergent vers RED-S subclinique. Le trade-off `COMPOSITION_COMPROMISED` était acknowledgé en mars mais les signaux suggèrent qu'on est en train de dépasser ce qui était raisonnable.

Décision attendue : `EnergyAssessment` (contrat B3) avec :
- `ea_status="low_normal"` (pas encore "subclinical" malgré 2 jours dedans)
- `cycle_context={phase: LUTEAL_LATE, modulation_applied: "+5% caloric recommendation pour phase lutéale"}`
- `recommendation.caloric_adjustment={direction: "up", magnitude: "moderate"}` : +200-300 kcal/jour pendant 2 semaines
- `recommendation.training_load_modulation={direction: "down", magnitude: "mild", duration_days: 14}` : réduire volume running -15% temporaire
- `recommendation.clinical_escalation=False` (pas encore, surveillance rapprochée)
- `recommendation.cycle_phase_considerations="Besoins énergétiques en phase lutéale tardive typiquement +5-10% vs folliculaire ; augmentation calorique à maintenir sur cycle complet puis réévaluer"`
- `flag_for_head_coach="Pattern de déficit énergétique sous-clinique en développement. Propose refeed accéléré + reduction modérée volume running pour 2 semaines. Revoir après prochain cycle menstruel."`
- `flag_for_recovery_coach=False` (pas de signal clinique critique ; Recovery suit déjà l'override pattern)

Composante énergie de `active_plan` à contribuer en regeneration de bloc : bloc "Refeed" (b2, upcoming) mérite peut-être d'être avancé ou étendu.

---

*Fin de l'annexe. Chaque exemple est un test-case candidat pour Phase D (tests d'intégration de `get_xxx_coach_view`).*
