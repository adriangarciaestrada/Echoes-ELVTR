// Copyright Echoes of the Architects. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

#include "GoapBlackboardTypes.generated.h"

UENUM(BlueprintType)
enum class EEchoesPlayerClass : uint8
{
	Hunter,
	Titan,
};

UENUM(BlueprintType)
enum class EKnightCombatState : uint8
{
	Active,
	Weaving,
	Downed,
};

/**
 * The facts La Costurera's squad plans against. The Witch's goal scoring
 * (PredictHunterDodge, MaintainWeave) and both Knights' goal scoring
 * (ProtectWitch, FlankTitanShield) read the same instance of this struct, so
 * "is Knight1 down" or "is the Witch mid-cast" has one answer during planning
 * instead of three brains each tracking their own copy and drifting apart.
 *
 * Field names match the design doc's blackboard keys exactly (including the
 * booleans, which skip the usual `b` prefix) so the two stay grep-comparable.
 */
USTRUCT(BlueprintType)
struct FGoapBlackboardState
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "GOAP|Blackboard")
	EEchoesPlayerClass PlayerClass = EEchoesPlayerClass::Hunter;

	/** 0 = never dodges that way, 1 = always. Feeds PredictHunterDodge's volley angle. */
	UPROPERTY(BlueprintReadOnly, Category = "GOAP|Blackboard")
	float HunterDodgeHabitScore = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "GOAP|Blackboard")
	bool TitanShieldActive = false;

	UPROPERTY(BlueprintReadOnly, Category = "GOAP|Blackboard")
	EKnightCombatState Knight1State = EKnightCombatState::Active;

	UPROPERTY(BlueprintReadOnly, Category = "GOAP|Blackboard")
	EKnightCombatState Knight2State = EKnightCombatState::Active;

	/** 0 = the weave just started, 1 = the downed knight is about to stand back up. */
	UPROPERTY(BlueprintReadOnly, Category = "GOAP|Blackboard")
	float ReviveWeaveProgress = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "GOAP|Blackboard")
	bool WitchVulnerable = false;
};
