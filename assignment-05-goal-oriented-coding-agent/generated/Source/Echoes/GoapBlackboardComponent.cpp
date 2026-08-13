// Copyright Echoes of the Architects. All Rights Reserved.

#include "GoapBlackboardComponent.h"

DEFINE_LOG_CATEGORY_STATIC(LogGoapBlackboard, Log, All);

UGoapBlackboardComponent::UGoapBlackboardComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UGoapBlackboardComponent::SetPlayerClass(EEchoesPlayerClass NewPlayerClass)
{
	Blackboard.PlayerClass = NewPlayerClass;
}

void UGoapBlackboardComponent::SetHunterDodgeHabitScore(float NewScore)
{
	Blackboard.HunterDodgeHabitScore = FMath::Clamp(NewScore, 0.0f, 1.0f);
}

void UGoapBlackboardComponent::SetTitanShieldActive(bool bActive)
{
	Blackboard.TitanShieldActive = bActive;
}

void UGoapBlackboardComponent::SetKnightState(int32 KnightIndex, EKnightCombatState NewState)
{
	if (KnightIndex == 1)
	{
		Blackboard.Knight1State = NewState;
		return;
	}
	if (KnightIndex == 2)
	{
		Blackboard.Knight2State = NewState;
		return;
	}

	const AActor* Owner = GetOwner();
	UE_LOG(LogGoapBlackboard, Warning,
		TEXT("%s: KnightIndex %d is neither 1 nor 2; state unchanged."),
		Owner ? *Owner->GetName() : TEXT("<no owner>"), KnightIndex);
}

EKnightCombatState UGoapBlackboardComponent::GetKnightState(int32 KnightIndex) const
{
	if (KnightIndex == 2)
	{
		return Blackboard.Knight2State;
	}

	if (KnightIndex != 1)
	{
		const AActor* Owner = GetOwner();
		UE_LOG(LogGoapBlackboard, Warning,
			TEXT("%s: KnightIndex %d is neither 1 nor 2; returning Knight1State."),
			Owner ? *Owner->GetName() : TEXT("<no owner>"), KnightIndex);
	}
	return Blackboard.Knight1State;
}

void UGoapBlackboardComponent::SetReviveWeaveProgress(float NewProgress)
{
	Blackboard.ReviveWeaveProgress = FMath::Clamp(NewProgress, 0.0f, 1.0f);
}

void UGoapBlackboardComponent::SetWitchVulnerable(bool bVulnerable)
{
	Blackboard.WitchVulnerable = bVulnerable;
}
