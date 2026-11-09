using System.Collections;
using UnityEngine;

namespace WatchYourBack
{

    public class AlertMovePatternState : IEnemyState
    {
        private const float LOOK_INTERVAL = 0.6f; // 방향당 바라보는 시간
        private readonly float arrivalConfirmDis = 0.2f; // 도착 인정거리
        


        public void Enter(EnemyStateManager manager)
        {
            Debug.Log("[AlertMovePattern] 알림 위치로 이동 시작");
            manager.Stop();
        } 




        public IEnumerator Execute(EnemyStateManager manager)
        {
            Vector2 targetPos = manager.LastPlayerPosition;

            while (true)
            {
                if (manager == null)
                {
                    yield break;
                }

                // 이동 중 플레이어 발견 시 즉시 Chase
                if (manager.CheckPlayerInSight() == true)
                {
                    manager.ChangeState(new EnemyChaseState());
                    yield break;
                }


                // 도착여부 체크
                float distance = Vector2.Distance(manager.transform.position, targetPos);
                if (distance <= arrivalConfirmDis)
                {
                    break; // 목표 지점 도달했으므로 탈출
                }

                // 이동 수행

                Vector2 dir = (targetPos - (Vector2)manager.transform.position).normalized;
                manager.MoveWithAvoidance(dir);
                               
                yield return null;

            }

            // 2단계 : 도착 후 4방향 탐색
            // 탐색 중에도 플레이어를 발견하면 즉시 Chase로 전환
            manager.Stop();

            Vector2[] directions = { Vector2.down, Vector2.right, Vector2.up, Vector2.left };

            foreach (Vector2 lookDir in directions)
            {
                manager.SetLookAround(lookDir);

                float timer = 0f;
                while (timer < LOOK_INTERVAL)
                {
                    if (manager == null)
                    {
                        yield break;
                    }

                    // 각 방향을 바라보는 도중에도 매 프레임 시야 체크
                    if (manager.CheckPlayerInSight() == true)
                    {
                        Debug.Log("[AlertMovePattern] 탐색 중 플레이어 발견 → Chase");
                        manager.ChangeState(new EnemyChaseState());
                        yield break;
                    }

                    timer += Time.deltaTime;
                    yield return null;
                }
            }

            // 3단계 : 탐색 완료 후 순찰 복귀
            Debug.Log("[AlertMovePattern] 탐색 완료 → Patrol 복귀");
            manager.ChangeState(new EnemyPatrolState());
        }

        public void Exit(EnemyStateManager manager) 
        { 
        
        }

        

       




    }

}


