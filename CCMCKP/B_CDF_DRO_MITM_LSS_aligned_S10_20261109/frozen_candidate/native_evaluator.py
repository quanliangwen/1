import math,heapq,itertools
import numpy as np


def _monte_carlo_evaluate(samples, T_max):
    '''
    :param samples: 1-D array of samples
    :param upper_value:
    :return:
    '''

    return len(np.where(samples < T_max)[0]) / len(samples)

def advanced_monte_carlo(factor_list, T_max, MC_sample_size, CL, param, quick_check_list):
    L,m = int(param[2]),int(param[0])
    _prob = 1- CL
    sign = 0
    _data_l = math.ceil(round(L**m * _prob)**(1/m))
    data_sum = np.sum([factor.get_index_sample(_data_l) for factor in factor_list])
    if data_sum >= T_max:
        # print(data_sum)
        sign = 1

    for i in range(len(quick_check_list)):
        data_sum = np.sum([factor_list[j].get_index_sample(quick_check_list[i][j]) for j in range(m)])
        # print(data_sum)
        if data_sum >= T_max:
            sign = 1

    if sign == 0:
        sum_samples = np.zeros(MC_sample_size)

        for factor in factor_list:
            cur_samples = factor.resample_multi(MC_sample_size)
            sum_samples += cur_samples
        
        return _monte_carlo_evaluate(sum_samples,T_max)
    
    else:
        return 0

def advanced_exact_evaluation(factor_list, T_max, MC_sample_size, CL, param, quick_check_list):
    '''
    advanced_exact_evaluation: 采用堆排序的方法，增加了快筛过程，并且降低了迭代的次数

    factor: Factor类item因子组成的待定解
    T_max: 时延上界
    CL: 置信度下界
    param: benchmark系数,[class数,item数,样本数,0,整数的CL]

    output: 因子list是否满足置信度的精确判断
    '''
    L,m = int(param[2]),int(param[0])
    _prob = 1 - CL
    _prob = float('{:.3f}'.format(_prob)) # 避免精度问题
    # k = math.ceil(L**m * _prob)
    queue = []
    samples_combination = []

    def push_q(D):    # D is a m-dimension list index of samples
        if all([v < L for v in D]):
            samples_sum = np.sum([factor_list[i].get_index_sample(D[i]) for i in range(m)])
            D.insert(0,-samples_sum)    # heap 默认弹出最小值，此处取负，实为最大值
            if D not in queue:
                heapq.heappush(queue,D)

    max_eval = math.ceil(L**m * _prob)
    _data_lz = math.ceil((L**m * _prob)**(1/m))
    sign = 0
    data_sum = np.sum([factor.get_index_sample(_data_lz) for factor in factor_list])

    if data_sum >= T_max:
        # print(data_sum)
        sign = 1

    for i in range(len(quick_check_list)):
        data_sum = np.sum([factor_list[j].get_index_sample(quick_check_list[i][j]) for j in range(m)])
        # print(data_sum)
        if data_sum >= T_max:
            sign = 1

    if sign == 0:
        
        while data_sum < T_max:
            if _data_lz > 0:
                _data_lz -= 1
                data_sum = np.sum([factor.get_index_sample(_data_lz) for factor in factor_list])
            else: 
                break
        
        select_pool = range(_data_lz + 2)   # 数据序号从[0,1,2,...,_data_lz,_data_lz+1]
        #  迭代生成数据组合
        for selected_cand_idx in itertools.product(select_pool, repeat = m):
            can_sample_list = list(selected_cand_idx)

            if _data_lz + 1 in can_sample_list:
                push_q(can_sample_list)    # 任何包含_data_lz + 1的数据组合都Push入队列中

        pop_factor_sample_sum = T_max + 1
        
        while queue and pop_factor_sample_sum > T_max:
            pop_solution = heapq.heappop(queue)
            samples_combination.append(pop_solution)

            for i in range(m):
                D = pop_solution[1:]   # 取出pop出数据组合的Index部分
                pop_factor_sample_sum = -pop_solution[0]    # 取出pop出数据组合的总时延部分

                if D[i]<L-1:
                    # 寻找pop出队列的数据组合的邻居，push入队列中
                    D[i] += 1
                    push_q(D)

            if len(samples_combination)>max_eval:
                return 0 # 直接判定为不可行解
        
        return 1-((len(samples_combination)+(_data_lz + 1)**m)/L**m)
    
    else:
        return 0