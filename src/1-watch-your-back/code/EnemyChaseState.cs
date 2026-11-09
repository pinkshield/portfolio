using System.Collections;
using UnityEngine;

namespace WatchYourBack
{
    public class EnemyChaseState : IEnemyState
    {
        private const float ArrivalThreshold = 0.2f;
        private const float LookAroundDuration = 2.0f;

        private Vector2 lastSeenPosition;

        public void Enter(EnemyStateManager manager)
        {

            Debug.Log("추적 상태 시작");
            if (SoundManager.Instance != null)
            {
                SoundManager.Instance.NotifyCombatStarted();
            }
        }

        
        public IEnumerator Execute(EnemyStateManager manager)
        {
            while (true)
            {
                bool canSeePlayer = manager.CheckPlayerInSight(); // 플레이어가 시아뱍스있는지 확인

                if (canSeePlayer == true)
                {
                    lastSeenPosition = manager.Player.position; // 실시간 위치 갱신

                    if (manager.CheckPlayerInAttackRange())
                    {
                        manager.ChangeState(new EnemyAttackState());
                        yield break;
                    }
                    else
                    {
                        Vector2 dir = (lastSeenPosition - (Vector2)manager.transform.position).normalized;
                        manager.MoveWithAvoidance(dir);
                    }
                }
                else
                {
                    // 플레이어를 놓쳤을 때: 마지막 목격 지점으로 이동 
                    float distToLastSeen = Vector2.Distance(manager.transform.position, lastSeenPosition);

                    if (distToLastSeen > ArrivalThreshold)
                    {
                        Vector2 dir = (lastSeenPosition - (Vector2)manager.transform.position).normalized;
                        manager.MoveWithAvoidance(dir);
                    }
                    else
                    {
                        // 목적지 도착 후 2초간 주변 탐색 연출 후 복귀 
                        manager.Stop();
                        yield return new WaitForSeconds(LookAroundDuration);
                        manager.ChangeState(new EnemyIdleState());
                        yield break;
                    }
                }
                yield return null;
            }
        }


        public void Exit(EnemyStateManager manager)
        {
            manager.Stop();
            SoundManager.Instance.NotifyCombatEnded(); 
        }
        
    }
}