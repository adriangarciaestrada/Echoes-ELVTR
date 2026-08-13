// Copyright Echoes of the Architects. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"

#include "GoapBlackboardTypes.h"

#include "GoapBlackboardComponent.generated.h"

/**
 * The squad's shared GOAP perception state, holding one FGoapBlackboardState.
 *
 * It belongs on the Witch, La Costurera, since she is the squad's anchor actor
 * and outlives either Knight going down. Each Knight AI controller keeps a
 * weak pointer to this instance (fetched from the Witch actor once at spawn)
 * rather than declaring its own component, which is what makes the blackboard
 * shared rather than three independent copies of the same seven facts.
 *
 * All writes go through the setters below rather than through the Blackboard
 * property directly, so the two progress values stay clamped to [0, 1] no
 * matter which brain — Witch or either Knight — is the one updating them.
 */
UCLASS(ClassGroup = (Echoes), meta = (BlueprintSpawnableComponent))
class ECHOES_API UGoapBlackboardComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGoapBlackboardComponent();

	/** Current squad-perception state. Read directly; write through the setters below. */
	UPROPERTY(BlueprintReadOnly, Category = "GOAP|Blackboard")
	FGoapBlackboardState Blackboard;

	UFUNCTION(BlueprintCallable, Category = "GOAP|Blackboard")
	void SetPlayerClass(EEchoesPlayerClass NewPlayerClass);

	UFUNCTION(BlueprintCallable, Category = "GOAP|Blackboard")
	void SetHunterDodgeHabitScore(float NewScore);

	UFUNCTION(BlueprintCallable, Category = "GOAP|Blackboard")
	void SetTitanShieldActive(bool bActive);

	/** KnightIndex is 1 or 2, matching the design doc's Knight1State/Knight2State keys. */
	UFUNCTION(BlueprintCallable, Category = "GOAP|Blackboard")
	void SetKnightState(int32 KnightIndex, EKnightCombatState NewState);

	/** KnightIndex is 1 or 2; any other value returns Knight1State and logs a warning. */
	UFUNCTION(BlueprintPure, Category = "GOAP|Blackboard")
	EKnightCombatState GetKnightState(int32 KnightIndex) const;

	UFUNCTION(BlueprintCallable, Category = "GOAP|Blackboard")
	void SetReviveWeaveProgress(float NewProgress);

	UFUNCTION(BlueprintCallable, Category = "GOAP|Blackboard")
	void SetWitchVulnerable(bool bVulnerable);

protected:
	virtual void BeginPlay() override {}
};
