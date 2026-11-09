using System.Collections;
using UnityEngine;

namespace WatchYourBack
{
    public class Watcher : MonoBehaviour
    {

        // 감시자는 Watchman의 눈 역할을 함께 해준다
        // 감시자의 시야에 들어오면 watchman은 해당 방향으로 간다. 

        // 감시자에게 필요한 것
        // 감시 시야 박스(collider)가 있어야함.
        // 물리 바디가 있어야 플레이어를 통과하지 못하게 해야함
        // ratman의 쥐처럼 지정해서 wachman을 움직이게 해야겠다.


        [Header("AlertTextbox")]
        [SerializeField] private GameObject alrertTextbox;


        [Header("SightRange")]
        [SerializeField] private Collider2D SightBox;


        [Header("Boss_Watchman")]
        public EnemyStateManager Watchman;

        [Header("Audio Settings")]
        [SerializeField] private AudioSource audioSource; // 
        [SerializeField] private AudioClip heySound;   // 



        private bool IsTextboxOn = false;
        private Rigidbody2D watcherRb;


        private void Awake()
        {
            watcherRb = GetComponent<Rigidbody2D>();

        }




        // 시야박스에 들어온 순간, Watchman을 불러온다 
        private void OnTriggerEnter2D(Collider2D collision)
        {
            if (Watchman == null) return;




            if (collision.CompareTag("Player") && Watchman.gameObject.activeSelf == true)
            {
                StartCoroutine(FindAlrert());
            }
        }

        private IEnumerator FindAlrert()
        {
            alrertTextbox.SetActive(true);
            IsTextboxOn = true;
            if (IsTextboxOn == true)
            {
                if (audioSource == null || heySound == null) yield break;
                audioSource.pitch = Random.Range(0.9f, 1.1f);
                audioSource.PlayOneShot(heySound);
            }
            

            yield return new WaitForSeconds(0.5f);
            IsTextboxOn = false;

            if (Watchman != null)
            {

                Watchman.LastPlayerPosition = SightBox.transform.position;
                Watchman.ChangeState(new AlertMovePatternState());
            }
            yield return new WaitForSeconds(0.5f);

            alrertTextbox.SetActive(false);
        }



    }

}



