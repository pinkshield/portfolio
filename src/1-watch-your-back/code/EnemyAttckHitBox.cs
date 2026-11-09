using UnityEngine;

namespace WatchYourBack
{
    public class EnemyAttackHitBox : MonoBehaviour
    {

        private EnemyStateManager manager;

        private void Awake()
        {
            manager = GetComponentInParent<EnemyStateManager>();
        }

        private void OnTriggerEnter2D(Collider2D collision)
        {

            if (collision.CompareTag("Player") == false) return;

            // 예외 처리: 이미 넉다운(다운/가짜다운) 확정된 적은 더 이상 공격 판정을 낼 수 없음
            if (manager != null && manager.IsKnockDown == true) return;


            //플레이어가 먼저 뒤통수를 친 경우 무시
            if (manager != null && manager.TryLockCombat() == false) return;

            
            PlayerMovement player = collision.GetComponent<PlayerMovement>();
            if (player != null)
            {
                player.KnockDown();
            }
            
        }
    }
}


