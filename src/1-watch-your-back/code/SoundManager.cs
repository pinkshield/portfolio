using Study.Utilities;
using System.Collections;
using UnityEngine;

namespace WatchYourBack
{
    public class SoundManager : SingletonBase<SoundManager>
    {
        [Header("BGM 설정")]
        [SerializeField] private AudioSource bgmSource;

        [Header("SFX 설정")]
        [SerializeField] private AudioSource sfxSource;

        [Header("= 전투 BGM 설정 =")]
        [SerializeField] private AudioClip normalBgmClip;   // 평상시 배경음
        [SerializeField] private AudioClip combatBgmClip;   // 전투(추격/공격) 배경음
        [SerializeField] private float bgmCrossfadeDuration = 1.0f; // 곡 전환 시 페이드 시간


        private int engagedEnemyCount = 0; // 현재 전투(추격/공격) 중인 적의 수
        private Coroutine bgmFadeCoroutine;

        public void NotifyCombatStarted()
        {
            if (bgmSource == null) return;

            engagedEnemyCount++;

            if (engagedEnemyCount == 1) // 0 -> 1, 첫 적이 전투를 시작한 순간
            {
                SwitchBgm(combatBgmClip);
            }
        }

        /// <summary>
        /// 적이 전투(추격 또는 공격) 상태에서 벗어났을 때 호출합니다
        /// </summary>
        public void NotifyCombatEnded()
        {
            if (bgmSource == null) return;

            engagedEnemyCount = Mathf.Max(0, engagedEnemyCount - 1);

            if (engagedEnemyCount == 0) // 마지막 적까지 전투에서 벗어난 순간
            {
                SwitchBgm(normalBgmClip);
            }
        }

        /// <summary>
        /// 진행 중인 페이드를 멈추고 새 곡으로 크로스페이드를 시작합니다
        /// </summary>
        private void SwitchBgm(AudioClip newClip)
        {
            if (bgmFadeCoroutine != null)
            {
                StopCoroutine(bgmFadeCoroutine);
            }

            bgmFadeCoroutine = StartCoroutine(CrossfadeBgm(newClip, bgmCrossfadeDuration));
        }

        /// <summary>
        /// 현재 곡의 볼륨을 낮췄다가, 새 곡으로 바꾸고 다시 볼륨을 올립니다
        /// </summary>
        private IEnumerator CrossfadeBgm(AudioClip newClip, float duration)
        {
            float originalVolume = bgmSource.volume;

            yield return FadeVolume(originalVolume, 0f, duration);

            bgmSource.clip = newClip;
            bgmSource.Play();

            yield return FadeVolume(0f, originalVolume, duration);
        }

        /// <summary>
        /// bgmAudioSource의 볼륨을 시작값에서 목표값까지 서서히 변경합니다
        /// </summary>
        private IEnumerator FadeVolume(float fromVolume, float toVolume, float duration)
        {
            float elapsedTime = 0f;

            while (elapsedTime < duration)
            {
                elapsedTime += Time.deltaTime;
                float progress = elapsedTime / duration;
                bgmSource.volume = Mathf.Lerp(fromVolume, toVolume, progress);

                yield return null;
            }

            bgmSource.volume = toVolume;
        }


        public void PlayBgm(AudioClip clip, bool loop = true)
        {
            if (clip == null) return;

            bgmSource.clip = clip;
            bgmSource.loop = loop;
            bgmSource.Play();
        }

        public void StopBgm()
        {
            bgmSource.Stop();
        }

        public void PlaySfx(AudioClip clip)
        {
            if (clip == null) return;
            sfxSource.PlayOneShot(clip);
        }

        /// <summary>
        /// 전투 BGM 카운터를 강제로 초기화합니다
        /// 씬이 재로드될 때, 이전 플레이에서 정리되지 못한 카운트가 남아있을 수 있어 호출합니다
        /// </summary>
        public void ResetCombatMusicState()
        {
            engagedEnemyCount = 0;

            if (bgmFadeCoroutine != null)
            {
                StopCoroutine(bgmFadeCoroutine);
            }

            if (bgmSource != null && normalBgmClip != null)
            {
                bgmSource.clip = normalBgmClip;
                bgmSource.volume = 1f;
                bgmSource.Play();
            }
        }

    }
}


