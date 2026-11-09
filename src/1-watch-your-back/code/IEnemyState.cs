using System.Collections;


namespace WatchYourBack
{ 
    // 모든 적 상태가 반드시 구현해야 하는 인터페이스
// MonoBehaviour를 상속하지 않는다 — 구조 정의용 파일이기 때문
    public interface IEnemyState
{
    // 상태에 진입할 때 한 번 호출된다
    void Enter(EnemyStateManager stateManager);

    // 상태의 실제 행동 루프 — Coroutine으로 실행된다
    IEnumerator Execute(EnemyStateManager stateManager);

    // 상태에서 빠져나올 때 한 번 호출된다
    void Exit(EnemyStateManager stateManager);
}
}

