using UnityEngine;

namespace WatchYourBack
{
    public class EnemyBackHurtBox : MonoBehaviour
    {
        private EnemyStateManager manager;

        private void Awake()
        {
            // 부모 객체의 매니저 참조 캐싱
            manager = GetComponentInParent<EnemyStateManager>();
        }

        private void OnTriggerEnter2D(Collider2D collision)
        {
            if (manager != null)
            {
                manager.OnBackHit(collision);
            }
        }
    }
}