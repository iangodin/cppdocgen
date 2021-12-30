
/// Class containing templated methods.
template<typename Value>
class Template
{
public:
    /// Template constructor.
    template<typename T>
    Template( T &&t );

    /// Variadic template constructor.
    template<typename ...T>
    Template( T &&...ts );

    /// Template method.
    template<typename R, typename T1, typename T2>
    R method1( const T1 &t1, const T2 &t2 );

    /// Variadic template method.
    template<typename ...T>
    void method2( T &&...ts );

    /// Variable from template.
    Value value;
};
