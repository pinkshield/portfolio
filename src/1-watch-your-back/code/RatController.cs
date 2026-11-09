using System;
using System.Collections;
using UnityEngine;

namespace WatchYourBack
{
    public class RatController : MonoBehaviour
    {

        // Ratman 의 수하 몬스터
        // 기본 상태
        // 좌우 움직임만 하는 단순 이동
        // 플레이어에게 닿게 되면 죽음 -> 죽는 순간 Ratman 이 죽은 쥐의 방향으로 이동 (Ratman 에게 보스패턴 스크립트 추가 예정)


        [Header("RatBasicSettings")]
        [SerializeField] private Collider2D deadHitBox;
        [SerializeField] private float moveSpeed;
        [SerializeField] private LayerMask wallLayer; // 벽감지용

        [Header("Movement Range")]
        [SerializeField] private float movementRange = 3f; // 좌우 이동 반경

        [Header("Boss_RatMan")]
        public EnemyStateManager Ratman;
       

        private Animator ratAnim;
        private Rigidbody2D ratRb;
        private Vector2 startPos;
        private int direction = 1; // 1: 오른쪽 , -1: 왼쪽
        private bool isDead = false;
         


        private void Awake()
        {
            ratAnim = GetComponent<Animator>();
            ratRb = GetComponent<Rigidbody2D>();

        }

        private void Start()
        {
            startPos = transform.position;
        }

        private void FixedUpdate()
        {
            ratMove();
        }

        private void OnTriggerEnter2D(Collider2D collision)
        {
            if (collision.CompareTag("Player"))
            {
                StartCoroutine(RatDie());
            }
            
        }


        private void ratMove()
        {
            // movementRange 사이를 왕복하는 값
            float pingPongX = Mathf.PingPong(Time.time * moveSpeed, movementRange *2);

            // 시작 위치와 왼쪽 끝에서부터 pingPongX만큼 더하여 실제 목표 X좌표 계산
            float targetX = (startPos.x - movementRange) + pingPongX;

            // 목표좌표가 ClampX 좌표와 다르다면 경계에 도달한 것
            int newDir = targetX > ratRb.position.x ? 1 : -1;
            if (newDir != direction)
            {
                direction = newDir; // 방향전환
                transform.localScale = new Vector3(direction, 1, 1);
            }

            ratRb.MovePosition(new Vector2(targetX,ratRb.position.y));
            ratAnim.SetBool("IsMoving", true);
        }

        private IEnumerator RatDie()
        {   
            if(isDead) yield  break;
            isDead = true;

            ratRb.linearVelocity = Vector2.zero;
            ratRb.simulated = false;

            ratAnim.SetTrigger("Dead");

            yield return new WaitForSeconds(1.0f);

            if (Ratman != null)
            {
                            
                Ratman.LastPlayerPosition = transform.position;
                Ratman.ChangeState(new AlertMovePatternState());
            }
            SpriteRenderer sr = GetComponent<SpriteRenderer>();
            if (sr != null)
            {
                sr.enabled = false;
            }

            // 콜라이더도 꺼서 플레이어와 다시 충돌하지 않게 한다
            Collider2D col = GetComponent<Collider2D>();
            if (col != null)
            {
                col.enabled = false;
            }


        }




    }
}


